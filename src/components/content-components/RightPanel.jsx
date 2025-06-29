import React, { useState, useEffect } from 'react';
import { PencilRuler } from 'lucide-react';
import path from 'path-browserify';

import Field from "./right-panel-components/Field";

import "./right-panel.css";
import { useDirectory } from '@/contexts/DirectoryContext';

function RightPanel() {
  const [hovered, setHovered] = useState(false);
  const [fileName, setFileName] = useState('');
  const [metadata, setMetadata] = useState({});
  const { selectedFile, setSelectedFile, setGlobalUpdateTimestamp, globalDirectory, setGlobalDirectory } = useDirectory();

  // Load metadata when file changes
  useEffect(() => {
    setFileName(selectedFile ? selectedFile.slice(0, -9) : '');
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
    window.electronAPI.renameFile((globalDirectory + '/' + selectedFile), newName)
      .then(result => {
        if (result.success) {
          setSelectedFile(newName + '.symphony');
          setGlobalUpdateTimestamp(Date.now());
        } else {
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

  return (
    <div className="content-panel-container">
      <div>
        <div className='med-title' text-style='display'>
          Details
        </div>
        <div className='field-label'>Title</div>
        <Field
          value={fileName}
          height='33px'
          onChange={e => updateTitle(e.target.value)}
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
        <Field initialValue="" height='32px' fontSize='1.2em' whiteSpace='nowrap' />
      </div>

      <button
        className='call-to-action'
        text-style='display'
        style={{ transition: 'filter 0.2s' }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={selectedFile ? (() => runPython2(selectedFile)) : (() => document.body.style.cursor = 'default')}>
        <div>Open in Editor</div>
        <PencilRuler size={16} strokeWidth={2.5} />
      </button>
    </div>
  );
}

export default RightPanel;
