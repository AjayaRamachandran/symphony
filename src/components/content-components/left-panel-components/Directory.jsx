import React, { useState, useEffect } from 'react';
import { FolderClosed, Plus } from 'lucide-react';
import directory from '@/assets/directory.json';

import Tooltip from '@/components/Tooltip';
import GenericModal from '@/modals/GenericModal';
import NewFolder from '@/modals/NewFolder';

import './directory.css'

function Directory() {
  const sections = ['Projects', 'Exports', 'Symphony Auto-Save'];
  const [isModalOpen, setModalOpen] = useState(false);

  return (
    <div className="directory">
      {sections.map((section, sectionIndex) => (
        <React.Fragment key={sectionIndex}>

          <div className="directory-large">
            {section}
            {section != 'Symphony Auto-Save' ? (
              <>
                <button className='tooltip' onClick={() => setModalOpen(true)}>
                  <Tooltip text="New Folder"/>
                  <Plus size={16} strokeWidth={1.5} />
                </button>
                <GenericModal isOpen={isModalOpen} onClose={() => setModalOpen(false)}>
                  <NewFolder />
                </GenericModal>
              </>
            ) : (
              <></>
            )}
          </div>

          {directory[section]?.map((element, elementIndex) => (
            <button className="directory-medium" key={elementIndex}>
              <FolderClosed style={{flexShrink: 0}} size={16} strokeWidth={1.5} color='#606060'/>
              <div style={{marginLeft: '6px'}}>
                {element}
              </div>
            </button>
          ))}

        </React.Fragment>
      ))}
    </div>
  );
}

export default Directory;