import React, { useState, useEffect } from 'react';
import { FolderOpen, ChartNoAxesGantt, Music, Save } from 'lucide-react';
import path from 'path-browserify';

import Field from '@/components/content-components/right-panel-components/Field';
import Dropdown from '@/components/Dropdown';
import Tooltip from '@/components/Tooltip';
import { useDirectory } from '@/contexts/DirectoryContext';

const options = [
  { label: 'Projects', icon: ChartNoAxesGantt },
  { label: 'Exports', icon: Music },
  { label: 'Symphony Auto-Save', icon: Save },
];

function NewFolder({defaultDestProp = '', onClose, onConflict}) {
  const [sourceLocation, setSourceLocation] = useState('');
  const [destination, setDestination] = useState('');
  const [projectName, setProjectName] = useState('');
  const { globalDirectory, setGlobalDirectory } = useDirectory();

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
      setProjectName(path.basename(result.replace(/\\/g, '/')));
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
      setGlobalDirectory(sourceLocation);
      onClose();
    } else {
      if (result.errorType === 409) {
        console.log(`Conflict: ${result.error}`);
        onConflict();
      } else {
        alert('Error: ' + result.error);
      }
    }
  };

  return (
    <>
      <div className='modal-title' text-style='display' style={{marginBottom : '25px'}}>Add New Folder</div>
      <div className='modal-body'>System File Location</div>
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
      <div className='modal-body' style={{ marginTop: '2em' }}>Folder Alias</div>
      <Field fontSize={'13px'} value={projectName} onChange={e => setProjectName(e.target.value)} />
      <div className='modal-body' style={{ marginTop: '2em' }}>Destination</div>
      <Dropdown options={options} onSelect={handleSelect} value={selectedOption}/>
      <button className={(sourceLocation == '' || destination == '' || projectName == '') ? 'call-to-action-2 locked' : 'call-to-action-2'} text-style='display' onClick={(sourceLocation == '' || destination == '' || projectName == '') ? null : addDirectory}>Add</button>
    </>
  );
}

export default NewFolder;