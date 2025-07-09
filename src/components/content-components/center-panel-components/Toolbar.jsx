import React, { useState, useEffect, useCallback } from 'react';
import { Copy, Scissors, Clipboard, CopyPlus, Users, Info, Star, FolderOpen, Trash2, FileAudio2, LayoutGrid, List, Rows2 } from 'lucide-react';
import path from 'path-browserify';

import mscz from '@/assets/mscz-icon.svg';
import Tooltip from '@/components/Tooltip';
import GenericModal from '@/modals/GenericModal';
import DeleteConfirmationModal from '@/modals/DeleteConfirmationModal';
import ShowInfoModal from '@/modals/ShowInfoModal';
import ExportModal from '@/modals/ExportModal';

import './toolbar.css'
import { useDirectory } from '@/contexts/DirectoryContext';

function Toolbar() {
  const { viewType, setViewType, clipboardFile, setClipboardFile, clipboardCut, setClipboardCut, selectedFile, setSelectedFile, globalDirectory, setGlobalUpdateTimestamp, isFieldSelected } = useDirectory();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const iconSize = 20

  const selectingSymphony = selectedFile && (selectedFile.slice(-9) === '.symphony')

  // Helper to call global operator functions
  const callOp = (op) => {
    if (window.symphonyOps && typeof window.symphonyOps[op] === 'function') {
      window.symphonyOps[op]();
    }
  };

  const openFileLocation = () => {
    if (selectedFile && globalDirectory) {
      window.electronAPI.openFileLocation(globalDirectory + '\\' + selectedFile);
    } else if (globalDirectory) {
      window.electronAPI.openNativeApp(globalDirectory);
    }
  }

  const handleDelete = useCallback(async () => {
    console.log(isFieldSelected);
    if ((selectedFile && globalDirectory)) {
      const filePath = path.join(globalDirectory, selectedFile);
      await window.electronAPI.deleteFile(filePath);
      setGlobalUpdateTimestamp(Date.now());
      setSelectedFile(null);
    }
  }, [selectedFile, globalDirectory, setGlobalUpdateTimestamp, isFieldSelected]);

  useEffect(() => {
    const handler = async (e) => {
      if ((e.key === 'Backspace' || e.key === 'Delete')) {if (!isFieldSelected) setShowDeleteConfirm(true); console.log(isFieldSelected)}
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
    }, [handleDelete]);

  return (
    <>
      <div className='toolbar-container scrollable light-bg'>
        <div className='toolbar-section'>
          EDIT
          <div className='toolbar-subsection'>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => {selectedFile ? callOp('handleCopy') : undefined}}><Tooltip text="Copy"/><Copy size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => {selectedFile ? callOp('handleCut') : undefined}}><Tooltip text="Cut"/><Scissors size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!clipboardFile ? ' grayed' : '')} onClick={() => {selectedFile ? callOp('handlePaste') : undefined}}><Tooltip text="Paste"/><Clipboard size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => {selectedFile ? callOp('handleDuplicate') : undefined}}><Tooltip text="Duplicate"/><CopyPlus size={iconSize}/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          SHARE / EXPORT
          <div className='toolbar-subsection'>
            <button className={'icon-button tooltip grayed'}><Tooltip text="Collaborate (Coming Soon)"/><Users size={iconSize}/></button>
            <button className={'icon-button tooltip grayed'}><Tooltip text="Export to MuseScore (Coming Soon)"/><img src={mscz} color={"#737373"} alt="mscz icon" width={iconSize} height={iconSize} /></button>
            <button className={'icon-button tooltip' + ((!selectedFile || !selectingSymphony) ? ' grayed' : '')} onClick={() => {(selectedFile && selectingSymphony) ? setShowExportModal(true) : undefined}}><Tooltip text="Export to Audio"/><FileAudio2 size={iconSize}/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          FILE
          <div className='toolbar-subsection'>
            <button className={'icon-button tooltip' + ((!selectedFile || !selectingSymphony) ? ' grayed' : '')} onClick={() => {(selectedFile && selectingSymphony) ? setShowInfo(true) : undefined}}><Tooltip text="See Properties"/><Info size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')}><Tooltip text="Star File"/><Star size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!globalDirectory ? ' grayed' : '')} onClick={() => {globalDirectory ? openFileLocation() : undefined}}><Tooltip text="Open File Location"/><FolderOpen size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => {selectedFile ? setShowDeleteConfirm(true) : undefined}}><Tooltip text="Delete"/><Trash2 size={iconSize} color='#E46767'/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          VIEW
          <div className='toolbar-subsection'>
            <button className={'icon-button tooltip' + (viewType === 'grid' ? ' chosen-view' : '')} onClick={() => setViewType('grid')}>
              <Tooltip text="Grid"/>
              <LayoutGrid size={iconSize}/>
            </button>
            <button className={'icon-button tooltip' + (viewType === 'list' ? ' chosen-view' : '')} onClick={() => setViewType('list')}>
              <Tooltip text="List"/>
              <List size={iconSize}/>
            </button>
            <button className={'icon-button tooltip' + (viewType === 'content' ? ' chosen-view' : '')} onClick={() => setViewType('content')}>
              <Tooltip text="Content"/>
              <Rows2 size={iconSize}/>
            </button>
          </div>
        </div>
      </div>
      <GenericModal isOpen={showDeleteConfirm} onClose={() => { setShowDeleteConfirm(false) }}>
        <DeleteConfirmationModal onComplete={() => { setShowDeleteConfirm(false); handleDelete() }} action={'Delete'} modifier={selectingSymphony ? 'Symphony' : '.wav file'} />
      </GenericModal>
      <GenericModal isOpen={showInfo} onClose={() => { setShowInfo(false) }}>
        <ShowInfoModal filePath={globalDirectory + '\\' + selectedFile}/>
      </GenericModal>
      <GenericModal isOpen={showExportModal} onClose={() => { setShowExportModal(false) }}>
        <ExportModal onClose={() => setShowExportModal(false) }/>
      </GenericModal>
    </>
  );
}

export default Toolbar;