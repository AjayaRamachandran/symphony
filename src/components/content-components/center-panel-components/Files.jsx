import React, { useState, useEffect } from 'react';
import { Search } from 'lucide-react';

import { useDirectory } from "@/contexts/DirectoryContext";

import "./files.css";
import NewFile from './files-components/NewFile';
import File from './files-components/File';

function Files() {
  const { globalDirectory, setGlobalDirectory, globalUpdateTimestamp, selectedFile, setSelectedFile, viewType } = useDirectory();
  const [symphonyFiles, setSymphonyFiles] = useState([]);
  const [currentSectionType, setCurrentSectionType] = useState(null);
  
  useEffect(() => {
    window.electronAPI.getSymphonyFiles(globalDirectory).then((files) => {
      setSymphonyFiles(files);
    });
    window.electronAPI.getSectionForPath(globalDirectory).then((type) => {
      setCurrentSectionType(type.section);
      console.log(type.section);
    });
  }, [globalDirectory, globalUpdateTimestamp]);

  return (
    <>
      {symphonyFiles == 'not a valid dir' ? <div className='empty-box'>No Folder Selected</div> : <></>}
      {symphonyFiles == 'no files' ? (
        <></>
      ) : (
        <>
          <div className={(viewType==='grid'? 'files' : 'files-row') + ' scrollable dark-bg'} onClick={e => { e.stopPropagation(); setSelectedFile(e.name); }}>
            {symphonyFiles == 'not a valid dir' ? <></> : <>{currentSectionType === 'Projects' ? <><NewFile /></> : undefined}
              {
                symphonyFiles.map((fileName, idx) => (
                <File key={idx} name={fileName} />))
              }</>
            }
          </div>
        </>
      )}
    </>
  );
}

export default Files;