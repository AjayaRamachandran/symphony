import React, { useState, useEffect } from 'react';
import { FolderClosed, Plus } from 'lucide-react';
import directory from '@/assets/directory.json';

import './directory.css'

function Directory() {
  const sections = ['Projects', 'Exports', 'Symphony Auto-Save'];

  return (
    <div className="directory">
      {sections.map((section, sectionIndex) => (
        <React.Fragment key={sectionIndex}>

          <div className="directory-large">
            {section}
            <button>
              <Plus size={18} strokeWidth={1.5} />
            </button>
            
          </div>

          {directory[section]?.map((element, elementIndex) => (
            <div className="directory-medium" key={elementIndex}>
              <FolderClosed style={{flexShrink: 0}} size={16} strokeWidth={1.5} color='#606060'/>
              <div style={{marginLeft: '6px'}}>
                {element}
              </div>
            </div>
          ))}

        </React.Fragment>
      ))}
    </div>
  );
}

export default Directory;