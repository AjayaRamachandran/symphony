import React, { useState } from 'react';
import { Plus } from 'lucide-react';

import "./new-file.css";
import { useDirectory } from '@/contexts/DirectoryContext';

import GenericModal from '@/modals/GenericModal';
import NewFileModal from '@/modals/NewFileModal';

function NewFile() {
  const { globalDirectory, setGlobalDirectory, setGlobalUpdateTimestamp, viewType } = useDirectory();
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
      <button className={'file-select-box' + (viewType==='grid'? '' : viewType==='content'? '-content' : '-list') + ' new'} onClick={() => setShowNewFile(true)}>
        <div className={'rounded-rect-icon' + (viewType==='grid'? '' : viewType==='content'? ' content' : ' list')}><Plus size={viewType==='list'? 14 : 40} color='#606060'/></div>
        <div style={{marginTop: (viewType=='grid'? '0px' : (viewType=='content' ? '15px' : '3px'))}}>New Symphony</div>
      </button>
      <GenericModal isOpen={showNewFile} onClose={() => setShowNewFile(false)}>
        <NewFileModal onClose={runPython}/>
      </GenericModal>
    </>
  );
}

export default NewFile;