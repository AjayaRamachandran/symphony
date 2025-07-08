import React, { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import path from 'path-browserify';

import fileIcon from '@/assets/file-icon.svg';
import wavIcon from '@/assets/wav-icon.svg';
import { useDirectory } from '@/contexts/DirectoryContext';

import "./file.css";

function File({name}) {
  const { globalDirectory, selectedFile, setSelectedFile, clipboardFile, clipboardCut, setGlobalUpdateTimestamp, viewType, tempFileName } = useDirectory();
  const [ fileName, setFileName ] = useState(name);
  const [ displayName, setDisplayName ] = useState(fileName);

  const runPython2 = async (title) => {
    console.log(title);
    setGlobalUpdateTimestamp(Date.now);
    const result = await window.electronAPI.runPythonScript(['open', `${title}`, globalDirectory]);
    console.log(result);
  };

  useEffect(() => {
    setFileName(name);
    //console.log(symphonyFiles);
  }, [selectedFile, name]);

  useEffect(() => {
    setDisplayName((selectedFile === name && tempFileName) ? tempFileName + '.symphony' : fileName);
    //console.log(symphonyFiles);
  }, [name, tempFileName, fileName]);

  // Use tempFileName if this file is selected
  //const displayName = (selectedFile === name && tempFileName) ? tempFileName + '.symphony' : fileName;

  return (
    <>
      <button className={'file-select-box' + (viewType==='grid'? '' : viewType==='content'? '-content' : '-list') + ((selectedFile === fileName) ? ' highlighted' : '')}
              style={{opacity: (clipboardFile && path.basename(clipboardFile) === fileName && clipboardCut)? 0.6 : 1}}
              onClick={e => { if (displayName.slice(-9) === '.symphony') e.stopPropagation(); setSelectedFile(fileName); console.log(fileName); }}
              onDoubleClick={async () => {(displayName.slice(-9) === '.symphony') ? runPython2(selectedFile) : await window.electronAPI.openNativeApp(globalDirectory + '\\' + displayName); setGlobalUpdateTimestamp(Date.now);
              }}>
        <img src={displayName.slice(-9) === '.symphony' ? fileIcon : wavIcon} color="#606060" height={viewType==='grid'? 78 : viewType==='content'?55: 21}
        style={{marginTop: (viewType==='list'? '3px' : '0')}} />
        <div style={{display: 'flex', flexDirection: viewType==='content'? 'column' : 'row'}}>
        <span
          style={{
            display: 'block',
            width: '100%',
            textAlign: viewType==='grid'?'center':'left',
            fontSize: '1em',
            marginTop: (viewType==='grid'? '1px' : '2px'),
            wordBreak: 'break-word', // break long words
            overflowWrap: 'break-word', // break long words
            whiteSpace: 'normal',
          }}
        >
          {displayName}
        </span>
        {viewType==='grid'? undefined : viewType==='content'?
        (<><span style={{opacity: 0.5, fontSize: '0.8em', marginTop: '7px'}}>{(displayName.slice(-9) === '.symphony') ? 'SYMPHONY File' : 'WAV Lossless Audio File'}</span></>) :
        (<><span style={{opacity: 0.5, fontSize: '1em', marginTop: '3px', width: '100%'}}>{(displayName.slice(-9) === '.symphony') ? 'SYMPHONY File' : 'WAV Lossless Audio File'}</span></>)
        }
        
        </div>
        
      </button>
    </>
  );
}

export default File;