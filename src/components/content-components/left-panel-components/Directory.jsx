import React, { useState, useEffect } from 'react';
import { FolderClosed, Plus, Pencil, X } from 'lucide-react';

import Tooltip from '@/components/Tooltip';
import GenericModal from '@/modals/GenericModal';
import NewFolder from '@/modals/NewFolder';
import EditModal from '@/modals/EditModal';
import AddAutoSave from '@/modals/AddAutoSave';
import DeleteConfirmationModal from '@/modals/DeleteConfirmationModal';
import SameNameWarning from '@/modals/SameNameWarning';

import { useDirectory } from "@/contexts/DirectoryContext";

import './directory.css'

function Directory() {
  const sections = ['Projects', 'Exports', 'Symphony Auto-Save'];
  //const [isModalOpen, setModalOpen] = useState(false);
  const { globalDirectory, setGlobalDirectory, setSelectedFile } = useDirectory();
  const [openSection, setOpenSection] = useState(null);
  const [directory, setDirectory] = useState(null);
  const [showAddAutoSave, setShowAddAutoSave] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [reload, setReload] = useState(0);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showSameNameWarning, setShowSameNameWarning] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null); // [section, dirName]

  const [hoverDirectory, setHoverDirectory] = useState(null);
  const [hoverName, setHoverName] = useState(null);
  const [hoverDest, setHoverDest] = useState(null);

  //console.log(Array.from(directory['Projects']))

  useEffect(() => {
    window.electronAPI.getDirectory().then(dir => {
      setDirectory(dir);

      const autoSaveArr = dir?.['Symphony Auto-Save'];
      const hasAutoSaveMapping = Array.isArray(autoSaveArr) && autoSaveArr.some(obj => obj['Auto-Save']);
      if (!hasAutoSaveMapping) {
        setShowAddAutoSave(true);
      }
    });
  }, [reload]);

  const reloadDirectory = () => setReload(r => r + 1);

  const getParams = () => {
    return {dir: hoverDirectory, name: hoverName, dest: hoverDest};
  }

  const toTuples = arr => arr.map(obj => {
    const key = Object.keys(obj)[0];
    return [key, obj[key]];
  });

  const callSetGlobalDirectory = (directory) => {
    console.log('Set global directory to ' + directory);
    setGlobalDirectory(directory.replace(/\\/g, '/'));
    setSelectedFile(null);
  };

  const removeDirectory = () => {
    console.log(pendingDelete);
    if (pendingDelete) {
      const [section, dirName] = pendingDelete;
      window.electronAPI.removeDirectory(section, dirName).then(() => {
        setShowDeleteConfirm(false);
        setPendingDelete(null);
        reloadDirectory();
      });
    }
  };

  if (!directory) return <div>Loading...</div>;

  return (
    <div className="directory scrollable med-bg">
      {sections.map((section, sectionIndex) => (
        <React.Fragment key={sectionIndex}>

          <div className="directory-large">
            {section}
            {section != 'Symphony Auto-Save' ? (
              <>
                <button className='tooltip' onClick={() => setOpenSection(section)}>
                  <Tooltip text="New Folder" positionOverride={['-90px', '25px']}/>
                  <Plus size={16} strokeWidth={1.5} />
                </button>
                <GenericModal isOpen={openSection === section} onClose={() => setOpenSection(null)}>
                  <NewFolder defaultDestProp={section} onConflict={() => { setShowSameNameWarning(true); }} onClose={() => { setOpenSection(null); reloadDirectory(); }}/>
                </GenericModal>
              </>
            ) : (
              <></>
            )}
          </div>
  
          {toTuples(directory[section]).map((elementPair, elementPairIndex) => (
            <div className="directory-medium" style={elementPair[1].replace(/\\/g, '/') == globalDirectory ? {filter: 'brightness(1.2)'} : {}} key={elementPairIndex} onClick={() => callSetGlobalDirectory(elementPair[1])}>
              <FolderClosed style={{flexShrink: 0}} size={16} strokeWidth={1.5} color='#606060'/>
              <div style={{display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignContent: 'center', width: '100%'}}>
                <span style={{marginLeft: '6px'}}>
                  {elementPair[0]}
                </span>
                <span style={{display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '3px'}}
                onClick={e => { e.stopPropagation(); setPendingDelete([section, elementPair[0]]); section === 'Symphony Auto-Save' ? setShowDeleteConfirm(true) : setShowEdit(true) }}
                onMouseEnter={() => {setHoverDirectory(elementPair[1]); setHoverName(elementPair[0]); setHoverDest(section)}}
                >
                  {section === 'Symphony Auto-Save' ? (<><X className='del-dir-button' size={14} /></>) :
                  (<><Pencil className='del-dir-button' size={14} /></>)}
                </span>
              </div>
            </div>
          ))}

        </React.Fragment>
      ))}
      <GenericModal isOpen={showAddAutoSave} onClose={() => setShowAddAutoSave(false)} showXButton={false}>
        <AddAutoSave onClose={() => { setShowAddAutoSave(false); reloadDirectory(); }} />
      </GenericModal>

      <GenericModal isOpen={showEdit} onClose={() => { setShowEdit(false); setPendingDelete(null); }}>
        <EditModal getParams={getParams} onConflict={() => { setShowSameNameWarning(true); }} onRefresh={() => { reloadDirectory() } } onClose={() => { setShowEdit(false); setPendingDelete(null); }} onDeny={() => { setShowSameNameWarning(true); setPendingDelete([getParams().dest, getParams().name]) }} onConfirm={() => { setShowDeleteConfirm(true);  }} onRemove={() => { removeDirectory(); }} />
      </GenericModal>

      <GenericModal isOpen={showDeleteConfirm} onClose={() => { setShowDeleteConfirm(false); setPendingDelete(null); }}>
        <DeleteConfirmationModal onComplete={() => { setShowDeleteConfirm(false); removeDirectory(); setShowEdit(false); setGlobalDirectory(null) }} action={'Remove'} modifier={'folder'} />
      </GenericModal>

      <GenericModal isOpen={showSameNameWarning} onClose={() => { setShowSameNameWarning(false) }} showXButton={false}>
        <SameNameWarning onComplete={() => { setShowSameNameWarning(false) }} />
      </GenericModal>
    </div>
  );
}

export default Directory;