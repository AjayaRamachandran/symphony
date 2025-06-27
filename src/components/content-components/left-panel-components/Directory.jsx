import React, { useState, useEffect } from 'react';
import { FolderClosed, Plus } from 'lucide-react';
import directory from '@/assets/directory.json';

import Tooltip from '@/components/Tooltip';
import GenericModal from '@/modals/GenericModal';
import NewFolder from '@/modals/NewFolder';

import { useDirectory } from "@/contexts/DirectoryContext";

import './directory.css'

function Directory() {
  const sections = ['Projects', 'Exports', 'Symphony Auto-Save'];
  //const [isModalOpen, setModalOpen] = useState(false);
  const { globalDirectory, setGlobalDirectory } = useDirectory();
  const [openSection, setOpenSection] = useState(null);

  //console.log(Array.from(directory['Projects']))

  const toTuples = arr => arr.map(obj => {
    const key = Object.keys(obj)[0];
    return [key, obj[key]];
  });

  const callSetGlobalDirectory = (directory) => {
    console.log('Set global directory to ' + directory)
    setGlobalDirectory(directory)
  };

  return (
    <div className="directory">
      {sections.map((section, sectionIndex) => (
        <React.Fragment key={sectionIndex}>

          <div className="directory-large">
            {section}
            {section != 'Symphony Auto-Save' ? (
              <>
                <button className='tooltip' onClick={() => setOpenSection(section)}>
                  <Tooltip text="New Folder"/>
                  <Plus size={16} strokeWidth={1.5} />
                </button>
                <GenericModal isOpen={openSection === section} onClose={() => setOpenSection(null)}>
                  <NewFolder defaultDestProp={section} onClose={() => setOpenSection(null)}/>
                </GenericModal>
              </>
            ) : (
              <></>
            )}
          </div>
  
          {toTuples(directory[section]).map((elementPair, elementPairIndex) => (
            <button className="directory-medium" style={elementPair[1] == globalDirectory ? {filter: 'brightness(1.2)'} : {}} key={elementPairIndex} onClick={() => callSetGlobalDirectory(elementPair[1])}>
              <FolderClosed style={{flexShrink: 0}} size={16} strokeWidth={1.5} color='#606060'/>
              <div style={{marginLeft: '6px'}}>
                {elementPair[0]}
              </div>
            </button>
          ))}

        </React.Fragment>
      ))}
    </div>
  );
}

export default Directory;