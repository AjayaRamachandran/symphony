// NewFolder.js
import React, { useState, useEffect } from 'react';
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

function NewFolder({defaultDestProp = '', onClose}) {
  const [sourceLocation, setSourceLocation] = useState('');
  const [destination, setDestination] = useState('');
  const [projectName, setProjectName] = useState('');
  useEffect(() => {
    if (defaultDestProp && destination === '') {
      setDestination(defaultDestProp);
      console.log(`defaultDestProp was set to ${defaultDestProp}`)
    }
  }, [defaultDestProp]);

  const selectedOption = options.find(opt => opt.label === destination) || null;

  const openFolderDialog = async () => {
    console.log('Button clicked');
    const result = await window.electronAPI.openDirectory();
    console.log('Dialog result:' + result);
    if (result) {
      setSourceLocation(result);
    }
  };

  const handleSelect = (selected) => {
    // selected is an object containing a label and an icon.
    setDestination(selected.label);
    //alert(`Selected: ${selected.label}`);
  };

  const addDirectory = async () => {
    const result = await window.electronAPI.saveDirectory({
      destination,
      projectName,
      sourceLocation,
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
      <div className='modal-title' text-style='display' style={{marginBottom : '25px'}}>Add New Folder</div>
      <div className='modal-body'>Project Name</div>
      <Field fontSize={'13px'} value={projectName} onChange={e => setProjectName(e.target.value)} />
      <div className='modal-body' style={{ marginTop: '2em' }}>Original File Location</div>
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
      <Dropdown options={options} onSelect={handleSelect} value={selectedOption}/>
      <button className={(sourceLocation == '' || destination == '' || projectName == '') ? 'call-to-action-2 locked' : 'call-to-action-2'} text-style='display' onClick={(sourceLocation == '' || destination == '' || projectName == '') ? null : addDirectory}>Add</button>
    </>
  );
}

export default NewFolder;
