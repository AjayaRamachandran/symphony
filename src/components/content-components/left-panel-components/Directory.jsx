import React, { useState, useEffect, useRef } from 'react';
import { FolderClosed, Plus, Pencil, X } from 'lucide-react';
import path from 'path-browserify';

import Tooltip from '@/components/Tooltip';
import GenericModal from '@/modals/GenericModal';
import NewFolder from '@/modals/NewFolder';
import EditModal from '@/modals/EditModal';
import AddAutoSave from '@/modals/AddAutoSave';
import DeleteConfirmationModal from '@/modals/DeleteConfirmationModal';
import SameNameWarning from '@/modals/SameNameWarning';
import InvalidDrop from '@/modals/InvalidDrop';
import SplashScreen from '@/modals/SplashScreen';

import { useDirectory } from "@/contexts/DirectoryContext";

import './directory.css';

function Directory() {
  const sections = ['Projects', 'Exports', 'Symphony Auto-Save'];
  const { globalDirectory, setGlobalDirectory, setSelectedFile, setGlobalUpdateTimestamp, showSplashScreen, setShowSplashScreen } = useDirectory();
  const [openSection, setOpenSection] = useState(null);
  const [directory, setDirectory] = useState(null);
  const [showAddAutoSave, setShowAddAutoSave] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [reload, setReload] = useState(0);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showSameNameWarning, setShowSameNameWarning] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [hoverDir, setHoverDir] = useState(null);
  const [hoverName, setHoverName] = useState(null);
  const [showInvalidModal, setShowInvalidModal] = useState(false);
  const dragCounter = useRef(0);

  // Track which directory is being dragged over for styling
  const [dragOverDir, setDragOverDir] = useState(null);

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

  useEffect(() => {
    if (!showAddAutoSave) {
      setShowSplashScreen(true);
    }
  }, [showAddAutoSave])

  const reloadDirectory = () => setReload(r => r + 1);

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
    if (pendingDelete) {
      const [section, dirName] = pendingDelete;
      window.electronAPI.removeDirectory(section, dirName).then(() => {
        setShowDeleteConfirm(false);
        setPendingDelete(null);
        reloadDirectory();
        setGlobalDirectory(null);
        setGlobalUpdateTimestamp(Date.now());
      });
    }
  };

  if (!directory) return <div>Loading...</div>;

  const onDragOver = (e) => {
    e.preventDefault();
  };


  const onDragEnter = (e, dir) => {
    e.preventDefault();
    dragCounter.current += 1;
    setDragOverDir(dir);
  };

  const onDragLeave = (e, dir) => {
    e.preventDefault();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setDragOverDir(null);
    }
  };

  const onDrop = (e, dir) => {
    e.preventDefault();
    dragCounter.current = 0;
    setDragOverDir(null);

    const files = Array.from(e.dataTransfer.files);
    const symphonyFiles = files.filter(file => file.name.endsWith('.symphony') || file.name.endsWith('wav'));

    if (symphonyFiles.length === 0) {
      setShowInvalidModal(true);
    }

    symphonyFiles.forEach(async (file) => {
      try {
        const arrayBuffer = await file.arrayBuffer();
        console.log(arrayBuffer, file.name, hoverDir);
        await window.electronAPI.moveFileRaw(arrayBuffer, file.name, hoverDir);
        setGlobalUpdateTimestamp(Date.now());
      } catch (err) {
        console.error("Error processing dropped file:", err);
      }
    });
    // Perform the click action for this directory
    callSetGlobalDirectory(dir);
  };

  return (
    <div className="directory scrollable med-bg">
      {sections.map((section, sectionIndex) => (
        <React.Fragment key={sectionIndex}>

          <div className="directory-large">
            {section}
            {section !== 'Symphony Auto-Save' && (
              <>
                <button className='tooltip' onClick={() => setOpenSection(section)}>
                  <Tooltip text="New Folder" positionOverride={['-90px', '25px']} />
                  <Plus size={16} strokeWidth={1.5} />
                </button>
                <GenericModal isOpen={openSection === section} onClose={() => setOpenSection(null)}>
                  <NewFolder
                    defaultDestProp={section}
                    onConflict={() => { setShowSameNameWarning(true); }}
                    onClose={() => { setOpenSection(null); reloadDirectory(); }}
                  />
                </GenericModal>
              </>
            )}
          </div>

          {toTuples(directory[section]).map((elementPair, elementPairIndex) => {
            const isSelected = elementPair[1].replace(/\\/g, '/') === globalDirectory;
            const isDragOver = dragOverDir === elementPair[1];

            return (
              <div
                key={elementPairIndex}
                className="directory-medium"
                style={{
                  filter: isSelected ? 'brightness(1.2)' : '',
                  outline: isDragOver ? '1px dashed #4A90E2' : 'none',
                  cursor: 'pointer'
                }}
                onClick={() => callSetGlobalDirectory(elementPair[1])}
                onMouseEnter={(e) => {setHoverDir(elementPair[1].replace(/\\/g, '/')); setHoverName(elementPair[0])}}
                onDragEnter={(e) => {onDragEnter(e, elementPair[1]); setHoverDir(elementPair[1].replace(/\\/g, '/')); console.log(hoverDir);}}
                onDragOver={onDragOver}
                onDragLeave={(e) => onDragLeave(e, elementPair[1])}
                onDrop={(e) => onDrop(e, elementPair[1])}
                // onMouseEnter={() => {setHoverDir(elementPair[1].replace(/\\/g, '/')); console.log(elementPair[1].replace(/\\/g, '/'))}}
              >
                <FolderClosed style={{ flexShrink: 0 }} size={16} strokeWidth={1.5} color='#606060' />
                <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignContent: 'center', width: '100%' }}>
                  <span className='directory-text' style={{ marginLeft: '6px' }}>
                    {elementPair[0]}
                  </span>
                  <span
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '3px' }}
                    onClick={e => {
                      e.stopPropagation();
                      setPendingDelete([section, elementPair[0]]);
                      section === 'Symphony Auto-Save' ? setShowDeleteConfirm(true) : setShowEdit(true);
                    }}
                  >
                    {section === 'Symphony Auto-Save' ? (<X className='del-dir-button' size={14} />) :
                      (<Pencil className='del-dir-button' size={14} />)}
                  </span>
                </div>
              </div>
            );
          })}
        </React.Fragment>
      ))}

      <GenericModal isOpen={showAddAutoSave} onClose={() => setShowAddAutoSave(false)} showXButton={false}>
        <AddAutoSave onClose={() => { setShowAddAutoSave(false); reloadDirectory(); }} />
      </GenericModal>
      <GenericModal isOpen={showSplashScreen} onClose={() => setShowSplashScreen(false)} showXButton={false} custom={'splash'}>
        <SplashScreen onComplete={() => { setShowSplashScreen(false); reloadDirectory(); }} />
      </GenericModal>

      <GenericModal isOpen={showEdit} onClose={() => { setShowEdit(false); setPendingDelete(null); }}>
        <EditModal
          getParams={async () => {console.log(hoverDir); return {dir: hoverDir, name: hoverName, dest: (await window.electronAPI.getSectionForPath(hoverDir)).section}}}
          onConflict={() => { setShowSameNameWarning(true); }}
          onRefresh={() => { reloadDirectory() }}
          onClose={() => { setShowEdit(false); setPendingDelete(null); }}
          onDeny={() => { setShowSameNameWarning(true); setPendingDelete(null) }}
          onConfirm={() => { setShowDeleteConfirm(true); }}
          onRemove={() => { removeDirectory(); }}
          onComplete={() => { setShowDeleteConfirm(false); removeDirectory(); setShowEdit(false); setGlobalDirectory(null); setSelectedFile(null); }}
        />
      </GenericModal>

      <GenericModal isOpen={showDeleteConfirm} onClose={() => { setShowDeleteConfirm(false); setPendingDelete(null); }}>
        <DeleteConfirmationModal onComplete={() => { setShowDeleteConfirm(false); removeDirectory(); setShowEdit(false); setGlobalDirectory(null) }} action={'Remove'} modifier={'folder'} />
      </GenericModal>
      <GenericModal isOpen={showInvalidModal} onClose={() => { setShowInvalidModal(false) }}>
        <InvalidDrop onComplete={() => setShowInvalidModal(false)} />
      </GenericModal>
      <GenericModal isOpen={showSameNameWarning} onClose={() => { setShowSameNameWarning(false) }} showXButton={false}>
        <SameNameWarning onComplete={() => { setShowSameNameWarning(false) }} />
      </GenericModal>
    </div>
  );
}

export default Directory;
