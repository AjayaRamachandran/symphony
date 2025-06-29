import React, { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';

import fileIcon from '@/assets/file-icon.svg';
import { useDirectory } from '@/contexts/DirectoryContext';

import "./file.css";

function File({name}) {
  const { globalDirectory, setGlobalDirectory, selectedFile, setSelectedFile } = useDirectory();
  const [ fileName, setFileName ] = useState(name);

  const runPython2 = async (title) => {
    console.log(title);
    document.body.style.cursor = 'wait';
    const result = await window.electronAPI.runPythonScript(['open', `${title}`, globalDirectory]);
    document.body.style.cursor = 'default';
    console.log(result);
  };

  useEffect(() => {
    setFileName(name);
    //console.log(symphonyFiles);
  }, [selectedFile, name]);

  return (
    <>
      <button className={'file-select-box' + ((selectedFile === fileName) ? ' highlighted' : '')}
              onClick={e => { e.stopPropagation(); setSelectedFile(fileName); console.log(fileName); }}
              onDoubleClick={() => runPython2(selectedFile)}>
        <img src={fileIcon} color="#606060" alt="mscz icon" width={110} />
        {fileName}
      </button>
    </>
  );
}

export default File;