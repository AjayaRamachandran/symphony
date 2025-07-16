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
  const { viewType, setViewType, clipboardFile, setClipboardFile, clipboardCut, setClipboardCut, selectedFile, setSelectedFile, globalDirectory, globalUpdateTimestamp, setGlobalUpdateTimestamp, isFieldSelected } = useDirectory();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [itemIsStarred, setItemIsStarred] = useState(false);
  const [settingsShowDelete, setSettingsShowDelete] = useState(true);
  const [actionKey, setActionKey] = useState('Ctrl');
  const iconSize = 20

  const selectingSymphony = selectedFile && (selectedFile.slice(-9) === '.symphony')

  useEffect(() => {
    window.electronAPI.getUserSettings().then((result) => {
      setSettingsShowDelete(!result["disable_delete_confirm"])
    })
  }, [selectedFile, globalUpdateTimestamp]);

  useEffect(() => {
    const isMac = navigator.userAgentData?.platform
      ? navigator.userAgentData.platform.toLowerCase().includes('mac')
      : navigator.platform.toLowerCase().includes('mac');

    setActionKey(isMac ? '⌘' : 'Ctrl');
  }, []);

  // Helper to call global operator functions
  const callOp = (op) => {
    if (window.symphonyOps && typeof window.symphonyOps[op] === 'function') {
      window.symphonyOps[op]();
    }
  };

  const openFileLocation = () => {
    if (selectedFile && globalDirectory) {
      window.electronAPI.openFileLocation(path.join(globalDirectory, selectedFile));
    } else if (globalDirectory) {
      window.electronAPI.openNativeApp(globalDirectory);
    }
  }

  const handleDelete = useCallback(async () => {
    //console.log(isFieldSelected);
    if ((selectedFile && globalDirectory)) {
      const filePath = path.join(globalDirectory, selectedFile);
      await window.electronAPI.deleteFile(filePath);
      setGlobalUpdateTimestamp(Date.now());
      setSelectedFile(null);
    }
  }, [selectedFile, globalDirectory, setGlobalUpdateTimestamp, isFieldSelected]);

  const isStarred = async (filePath) => {
    try {
      const stars = await window.electronAPI.getStars();
      console.log(stars)
      //console.log(filePath)
      // Normalize input path
      const normalizedTarget = path.normalize(filePath).replace(/\\/g, '/');

      return stars.some((starPath) => {
        const normalizedStar = path.normalize(starPath).replace(/\\/g, '/');
        //console.log(normalizedStar);
        //console.log(normalizedTarget);
        return normalizedStar === normalizedTarget;
      });
    } catch(e) {
      return false;
    }
  };

  useEffect(() => {
    try {
      isStarred(path.join(globalDirectory, selectedFile)).then((result) => {
      setItemIsStarred(result);
    })} catch (e) {

    }
  }, [selectedFile])

  const handleStarToggle = async () => {
    if (!selectedFile) return;

    const filePath = path.join(globalDirectory, selectedFile);
    const starred = await isStarred(filePath);
    //console.log(starred)
    setItemIsStarred(!starred);

    if (!starred) {
      await window.electronAPI.addStar(filePath);
    } else {
      await window.electronAPI.removeStar(filePath);
    }
    setGlobalUpdateTimestamp(Date.now());
  };

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
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => {selectedFile ? callOp('handleCopy') : undefined}}><Tooltip text="Copy" altText={`(${actionKey}+C)`}/><Copy size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => {selectedFile ? callOp('handleCut') : undefined}}><Tooltip text="Cut" altText={`(${actionKey}+X)`}/><Scissors size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!clipboardFile ? ' grayed' : '')} onClick={() => {selectedFile ? callOp('handlePaste') : undefined}}><Tooltip text="Paste" altText={`(${actionKey}+V)`}/><Clipboard size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => {selectedFile ? callOp('handleDuplicate') : undefined}}><Tooltip text="Duplicate" altText={`(${actionKey}+D)`}/><CopyPlus size={iconSize}/></button>
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
            <button
              className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')}
              onClick={handleStarToggle}
              disabled={!selectedFile}
            >
              <Tooltip text="Star File" />
              {(itemIsStarred && selectedFile) ?
              (<><i className="bi bi-star-fill" style={{fontSize: '20px'}}></i></>) : (<><i className="bi bi-star" style={{fontSize: '20px'}}></i></>)}
            </button>
            <button className={'icon-button tooltip' + (!globalDirectory ? ' grayed' : '')} onClick={() => {globalDirectory ? openFileLocation() : undefined}}><Tooltip text="Open File Location"/><FolderOpen size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => {if (settingsShowDelete) {selectedFile ? setShowDeleteConfirm(true) : undefined} else {selectedFile ? handleDelete() : undefined}}}><Tooltip text="Delete" altText={`(Del/Bkspc)`}/><Trash2 size={iconSize} color='#E46767'/></button>
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
      {showInfo && selectedFile && globalDirectory && (
        <GenericModal isOpen={showInfo} onClose={() => { setShowInfo(false) }}>
          <ShowInfoModal filePath={path.join(globalDirectory, selectedFile)} />
        </GenericModal>
      )}
      <GenericModal isOpen={showExportModal} onClose={() => { setShowExportModal(false) }}>
        <ExportModal onClose={() => setShowExportModal(false) }/>
      </GenericModal>
    </>
  );
}

export default Toolbar;