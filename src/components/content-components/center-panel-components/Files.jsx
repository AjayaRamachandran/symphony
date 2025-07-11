import React, { useState, useEffect, useCallback } from 'react';
import { Search } from 'lucide-react';

import { useDirectory } from "@/contexts/DirectoryContext";

import "./files.css";
import NewFile from './files-components/NewFile';
import File from './files-components/File';

import InvalidDrop from '@/modals/InvalidDrop';
import GenericModal from '@/modals/GenericModal';

function Files() {
  const {
    globalDirectory,
    globalUpdateTimestamp,
    setGlobalUpdateTimestamp,
    selectedFile,
    setSelectedFile,
    viewType,
    setGlobalStars,
    globalStars
  } = useDirectory();

  const [symphonyFiles, setSymphonyFiles] = useState([]);
  const [currentSectionType, setCurrentSectionType] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showInvalidModal, setShowInvalidModal] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setGlobalUpdateTimestamp(Date.now());
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!globalDirectory) return;

    window.electronAPI.getSymphonyFiles(globalDirectory).then((files) => {
      setSymphonyFiles(files);
    });

    window.electronAPI.getSectionForPath(globalDirectory).then((type) => {
      setCurrentSectionType(type.section);
    });

    // Fetch all starred files once for this directory
    window.electronAPI.getStars().then((stars) => {
      const normalizedStars = stars.map((s) => s.replace(/\\/g, '/'));
      setGlobalStars(normalizedStars);
    });
  }, [globalDirectory, globalUpdateTimestamp]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const symphonyFiles = files.filter(file => file.name.endsWith('.symphony') || file.name.endsWith('.wav'));

    if (symphonyFiles.length === 0) {
      setShowInvalidModal(true);
    }

    symphonyFiles.forEach(async (file) => {
      try {
        const arrayBuffer = await file.arrayBuffer();
        await window.electronAPI.moveFileRaw(arrayBuffer, file.name, globalDirectory);
        setGlobalUpdateTimestamp(Date.now());
      } catch (err) {
        console.error("Error processing dropped file:", err);
      }
    });
  }, [globalDirectory, setGlobalUpdateTimestamp]);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  return (
    <>
      {symphonyFiles === 'not a valid dir' ? <div className='empty-box'>No Folder Selected</div> : null}
      {symphonyFiles === 'no files' ? null : (
        <div
          className={(viewType === 'grid' ? 'files' : 'files-row') + ' scrollable dark-bg'}
          onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          style={{ outline: isDragging ? '1px dashed #737373' : 'none', filter: isDragging ? 'brightness(1.1)' : 'none' }}
        >
          {currentSectionType === 'Projects' && <NewFile />}
          {Array.isArray(symphonyFiles) && symphonyFiles.map((fileName, idx) => (
            <File key={idx} name={fileName} />
          ))}
        </div>
      )}
      <GenericModal isOpen={showInvalidModal} onClose={() => { setShowInvalidModal(false) }}>
        <InvalidDrop onComplete={() => setShowInvalidModal(false)} />
      </GenericModal>
    </>
  );
}

export default Files;
