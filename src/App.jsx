import React, { useEffect, useCallback } from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import { useDirectory } from '@/contexts/DirectoryContext';
import path from 'path-browserify';

function App() {
  const {
    selectedFile, globalDirectory, clipboardFile, setClipboardFile, clipboardCut, setClipboardCut, setGlobalUpdateTimestamp
  } = useDirectory();

  // Operator functions
  const handleCopy = useCallback(() => {
    if (selectedFile && globalDirectory) {
      setClipboardFile(path.join(globalDirectory, selectedFile));
      setClipboardCut(false);
    }
  }, [selectedFile, globalDirectory, setClipboardFile, setClipboardCut]);

  const handleCut = useCallback(() => {
    if (selectedFile && globalDirectory) {
      setClipboardFile(path.join(globalDirectory, selectedFile));
      setClipboardCut(true);
    }
  }, [selectedFile, globalDirectory, setClipboardFile, setClipboardCut]);

  const handlePaste = useCallback(async () => {
    if (clipboardFile && globalDirectory) {
      const baseName = path.basename(clipboardFile);
      let destPath = path.join(globalDirectory, baseName);
      let finalDest = destPath;
      let counter = 1;
      while (await window.electronAPI.fileExists(finalDest)) {
        const ext = path.extname(baseName);
        const name = path.basename(baseName, ext);
        finalDest = path.join(globalDirectory, `${name} (copy${counter > 1 ? ' ' + counter : ''})${ext}`);
        counter++;
      }
      await window.electronAPI.copyFile(clipboardFile, finalDest);
      setGlobalUpdateTimestamp(Date.now());
      if (clipboardCut) {
        await window.electronAPI.deleteFile(clipboardFile);
        setClipboardFile(null);
        setClipboardCut(false);
      }
    }
  }, [clipboardFile, clipboardCut, globalDirectory, setClipboardFile, setClipboardCut, setGlobalUpdateTimestamp]);

  const handleDuplicate = useCallback(async () => {
    if (selectedFile && globalDirectory) {
      const srcPath = path.join(globalDirectory, selectedFile);
      const baseName = path.basename(selectedFile);
      let destPath = path.join(globalDirectory, baseName);
      let finalDest = destPath;
      let counter = 1;
      while (await window.electronAPI.fileExists(finalDest)) {
        const ext = path.extname(baseName);
        const name = path.basename(baseName, ext);
        finalDest = path.join(globalDirectory, `${name} (copy${counter > 1 ? ' ' + counter : ''})${ext}`);
        counter++;
      }
      await window.electronAPI.copyFile(srcPath, finalDest);
      setGlobalUpdateTimestamp(Date.now());
    }
  }, [selectedFile, globalDirectory, setGlobalUpdateTimestamp]);

  const handleDelete = useCallback(async () => {
    if (selectedFile && globalDirectory) {
      const filePath = path.join(globalDirectory, selectedFile);
      await window.electronAPI.deleteFile(filePath);
      setGlobalUpdateTimestamp(Date.now());
    }
  }, [selectedFile, globalDirectory, setGlobalUpdateTimestamp]);

  useEffect(() => {
    const handler = async (e) => {
      if (e.key === 'F12') {
        window.electronAPI.toggleDevTools();
      }
      if (e.key === 'Backspace' || e.key === 'Delete') await handleDelete();
      if (e.ctrlKey && e.key.toLowerCase() === 'c') handleCopy();
      if (e.ctrlKey && e.key.toLowerCase() === 'x') handleCut();
      if (e.ctrlKey && e.key.toLowerCase() === 'v') await handlePaste();
      if (e.ctrlKey && e.key.toLowerCase() === 'd') await handleDuplicate();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleCopy, handleCut, handlePaste, handleDuplicate, handleDelete]);

  // Attach operator functions to window for Toolbar access
  window.symphonyOps = {
    handleCopy,
    handleCut,
    handlePaste,
    handleDuplicate,
    handleDelete
  };

  return (
    <>
      <Router>
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>
      </Router>
    </>
  )
}

export default App