import React, { useState, useEffect } from 'react';
import { PencilRuler } from 'lucide-react';
import path from 'path-browserify';

import Field from "./right-panel-components/Field";
import Tooltip from '@/components/Tooltip';

import "./right-panel.css";
import { useDirectory } from '@/contexts/DirectoryContext';
import NewFile from './center-panel-components/files-components/NewFile';

function RightPanel() {
  const [hovered, setHovered] = useState(false);
  const [fileName, setFileName] = useState('');
  const [metadata, setMetadata] = useState({});
  const {
    selectedFile, setSelectedFile, setGlobalUpdateTimestamp, globalDirectory, setGlobalDirectory,
    tempFileName, setTempFileName
  } = useDirectory();

  // Load metadata when file changes
  useEffect(() => {
    setFileName(selectedFile ? selectedFile.slice(0, -9) : '');
    setTempFileName(selectedFile ? selectedFile.slice(0, -9) : '');
    if (selectedFile && globalDirectory) {
      window.electronAPI.getMetadata(globalDirectory + '/' + selectedFile)
        .then(meta => setMetadata(meta || {}));
    } else {
      setMetadata({});
    }
  }, [selectedFile, globalDirectory]);

  const runPython2 = async (title) => {
    console.log(title);
    document.body.style.cursor = 'wait';
    const result = await window.electronAPI.runPythonScript(['open', `${title}`, globalDirectory]);
    document.body.style.cursor = 'default';
    console.log(result);
  };

  const updateTitle = (newName) => {
    console.log(selectedFile);
    console.log(globalDirectory);
    console.log(newName);

    window.electronAPI.renameFile((globalDirectory + '\\' + selectedFile), newName)
      .then(result => {
        if (result.success) {
          setSelectedFile(newName + '.symphony');
          setGlobalUpdateTimestamp(Date.now());
          console.log(`RightPanel.jsx::updateTitle() - newName: ${newName}`);
        } else {
          setSelectedFile(newName + '.symphony');
          setGlobalUpdateTimestamp(Date.now());
          console.error(result.error);
        }
      });
  };

  // Helper to update a metadata field and persist it
  const updateMetadataField = (field, value) => {
    if (!selectedFile || !globalDirectory) return;
    const newMeta = { ...metadata, [field]: value };
    setMetadata(newMeta);
    window.electronAPI.setMetadata(globalDirectory + '/' + selectedFile, newMeta);
  };

  // Only update tempFileName on change, and update actual file on blur
  const handleTitleChange = (e) => {
    setTempFileName(e.target.value);
  };
  const handleTitleBlur = (e) => {
    if (tempFileName !== fileName) {
      updateTitle(tempFileName);
    }
  };

  return (
    <div className="content-panel-container">
      <>
        <div>
          <div className='med-title' text-style='display'>Details</div>
          {selectedFile ? (<>
          <div className='field-label'>Title</div>
          <Field
            value={tempFileName}
            height='33px'
            onChange={handleTitleChange}
            onBlur={handleTitleBlur}
            singleLine={true}
          />

          <div className='field-label'>Description</div>
          <Field
            value={metadata.Description || ''}
            height='120px'
            fontSize='1.2em'
            onChange={e => updateMetadataField('Description', e.target.value)}
          />

          <div className='field-label'>Composer / Arr.</div>
          <Field
            value={metadata.Composer || ''}
            height='70px'
            fontSize='1.2em'
            onChange={e => updateMetadataField('Composer', e.target.value)}
          />

          <div className='field-label'>Collaborators</div>
          <Field
            value={metadata.Collaborators || ''}
            height='70px'
            fontSize='1.2em'
            onChange={e => updateMetadataField('Collaborators', e.target.value)}
          />

          <div className='field-label'>File Location</div>
          <div className='field scrollable dark-bg' style={{whiteSpace: 'nowrap', textOverflow: 'unset',
            overflowX: 'scroll', padding: '7px 7px 2px 7px', fontSize: '13px', cursor: 'pointer', fontStyle: 'italic'}}>
            <Tooltip text={globalDirectory.replace(/\\/g, '/') + '/' + selectedFile} />
            {globalDirectory.replace(/\\/g, '/') + '/' + selectedFile}
          </div>
          </>) : (<><div className='faded'>Select a file to view its details.</div></>) }
        </div>

        
          <button
            className={'call-to-action tooltip' + (selectedFile ? '' : ' inactive')}
            text-style='display'
            style={{ transition: 'filter 0.2s, border 0.4s, background 0.4s' }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            onClick={selectedFile ? () => runPython2(selectedFile) : undefined}
          >
            <Tooltip text={selectedFile ? 'Open this Symphony in the dedicated editor.' : 'Select a Symphony to open it in the editor.'}/>
            <div>Open in Editor</div>
            <PencilRuler size={16} strokeWidth={2.5} />
          </button>
      </>
    </div>
  );
}

export default RightPanel;
