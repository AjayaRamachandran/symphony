// NewFolder.js
import React, { useState, useEffect } from 'react';
import { FolderOpen } from 'lucide-react';

//import Field from '@/components/content-components/right-panel-components/Field';
//import Dropdown from '@/components/Dropdown';
import Tooltip from '@/components/Tooltip';

//console.log('electronAPI:', window.electronAPI);


function AddAutoSave({onClose}) {
  const [sourceLocation, setSourceLocation] = useState('');
  const destination = 'Symphony Auto-Save'
  const projectName = 'Auto-Save'

  const openFolderDialog = async () => {
    console.log('Button clicked');
    const result = await window.electronAPI.openDirectory();
    console.log('Dialog result:' + result);
    if (result) {
      setSourceLocation(result);
    }
  };


  const addDirectory = async () => {
    const result = await window.electronAPI.saveDirectory({
      destination : destination,
      projectName : projectName,
      sourceLocation : sourceLocation,
    });
    if (result.success) {
      console.log(`Directory added: ${[projectName, destination, sourceLocation]}`);
      // Optionally reset fields or close modal
    } else {
      alert('Error: ' + result.error);
    }
    onClose()
  };

  return (
    <>
      <div className='modal-title' text-style='display'>Set Up Auto-Save</div>
      <div className='modal-paragraph'>Let's choose a destination for your Auto-Save files so you can easily recover your work if needed.</div>
      <div className='tooltip'>
        <button className='modal-file-explorer-button' onClick={openFolderDialog}>
          <FolderOpen size={16} style={{ marginRight: '8px', flexShrink: 0 }} />
          <span
            style={{
              overflow: 'hidden',
              whiteSpace: 'nowrap',
              textOverflow: 'ellipsis',
              display: 'inline-block',
              flexGrow: 1,
              minWidth: 0,
            }}
          >
            {sourceLocation == "" ? 'Open File Explorer...' : sourceLocation}
          </span>
        </button>
        {sourceLocation != '' ? (
          <div style={{transform: 'translateY(-40px)'}}><Tooltip text={`${sourceLocation}  ⦁  Click to Change`} /></div>
        ) : ''}
      </div>
      <div style={{display: 'flex', justifyContent: 'space-between'}}>
        <div className='modal-whisper'>You can change this at any time.</div>
        <button className={(sourceLocation == '' || destination == '' || projectName == '') ? 'call-to-action-2 locked' : 'call-to-action-2'} text-style='display' onClick={(sourceLocation == '' || destination == '' || projectName == '') ? null : addDirectory}>Done</button>
      </div>
    </>
  );
}

export default AddAutoSave;
