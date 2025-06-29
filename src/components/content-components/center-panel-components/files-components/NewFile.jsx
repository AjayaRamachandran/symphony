import React, { useState } from 'react';
import { Plus } from 'lucide-react';

import "./new-file.css";
import { useDirectory } from '@/contexts/DirectoryContext';

import GenericModal from '@/modals/GenericModal';
import NewFileModal from '@/modals/NewFileModal';

function NewFile() {
  const { globalDirectory, setGlobalDirectory, setGlobalUpdateTimestamp } = useDirectory();
  const [showNewFile, setShowNewFile] = useState(false);

  const runPython = async (title) => {
    console.log(title);
    document.body.style.cursor = 'wait';
    const result = await window.electronAPI.runPythonScript(['instantiate', `${title}.symphony`, globalDirectory]);
    document.body.style.cursor = 'default';
    console.log(result);
    setShowNewFile(false);
    setGlobalUpdateTimestamp(Date.now());
  };

  return (
    <>
      <button className='file-select-box new' onClick={() => setShowNewFile(true)}>
        <div className='rounded-rect-icon'><Plus size={40} color='#606060'/></div>
        New Symphony
      </button>
      <GenericModal isOpen={showNewFile} onClose={() => setShowNewFile(false)}>
        <NewFileModal onClose={runPython}/>
      </GenericModal>
    </>
  );
}

export default NewFile;