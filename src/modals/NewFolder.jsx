// NewFolder.js
import React, { useState } from 'react';
import { FolderOpen, ChartNoAxesGantt, Music, Save } from 'lucide-react';

import Field from '@/components/content-components/right-panel-components/Field';
import Dropdown from '@/components/Dropdown';
import Tooltip from '@/components/Tooltip';

//console.log('electronAPI:', window.electronAPI);

const options = [
  { label: 'Projects', icon: ChartNoAxesGantt },
  { label: 'Exports', icon: Music },
  { label: 'Symphony Auto-Save', icon: Save },
];

function NewFolder() {
  const [sourceLocation, setSourceLocation] = useState('');
  const [destination, setDestination] = useState('');

  const openFolderDialog = async () => {
    console.log('Button clicked');
    const result = await window.electronAPI.openDirectory();
    console.log('Dialog result:', result);
    if (result) {
      setSourceLocation(result);
    }
  };

  const handleSelect = (selected) => {
    setDestination(selected)
    alert('Selected:', selected);
  };

  const addDirectory = () => {
    alert('button clicked');
  };

  return (
    <>
      <div className='modal-title' text-style='display'>Add New Folder</div>
      <div className='modal-body'>Original File Location</div>
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
      <div className='modal-body' style={{ marginTop: '2em' }}>Destination</div>
      <Dropdown options={options} onSelect={handleSelect} />
      <button className={(sourceLocation == '' || destination == '') ? 'call-to-action-2 locked' : 'call-to-action-2'} text-style='display' onClick={(sourceLocation == '') ? null : addDirectory}>Add</button>
    </>
  );
}

export default NewFolder;
