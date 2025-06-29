import React, { useState, useEffect } from 'react';
import { Search } from 'lucide-react';

import { useDirectory } from "@/contexts/DirectoryContext";

import "./files.css";
import NewFile from './files-components/NewFile';
import File from './files-components/File';

function Files() {
  const { globalDirectory, setGlobalDirectory, globalUpdateTimestamp, selectedFile, setSelectedFile } = useDirectory();
  const [symphonyFiles, setSymphonyFiles] = useState([]);
  
  useEffect(() => {
    window.electronAPI.getSymphonyFiles(globalDirectory).then((files) => {
      setSymphonyFiles(files);
    });
    //console.log(symphonyFiles);
  }, [globalDirectory, globalUpdateTimestamp]);

  return (
    <>
      {symphonyFiles == 'not a valid dir' ? <div className='empty-box'>No Folder Selected</div> : <></>}
      {symphonyFiles == 'no files' ? (
        <></>
      ) : (
        <>
          <div className='files scrollable dark-bg' onClick={e => { e.stopPropagation(); setSelectedFile(name); }}>
            {symphonyFiles == 'not a valid dir' ? <></> : <><NewFile />
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