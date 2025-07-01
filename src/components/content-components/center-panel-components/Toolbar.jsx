import React, { useState, useEffect } from 'react';
import { Copy, Scissors, Clipboard, CopyPlus, Users, KeyRound, Tag, FolderOpen, Trash2, FileAudio2, LayoutGrid, List, Rows2 } from 'lucide-react';

import mscz from '@/assets/mscz-icon.svg';
import Tooltip from '@/components/Tooltip';
import GenericModal from '@/modals/GenericModal';
import DeleteConfirmationModal from '@/modals/DeleteConfirmationModal';

import './toolbar.css'
import { useDirectory } from '@/contexts/DirectoryContext';

function Toolbar() {
  const { viewType, setViewType, clipboardFile, setClipboardFile, clipboardCut, setClipboardCut, selectedFile, globalDirectory } = useDirectory();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)  
  const iconSize = 20

  // Helper to call global operator functions
  const callOp = (op) => {
    if (window.symphonyOps && typeof window.symphonyOps[op] === 'function') {
      window.symphonyOps[op]();
    }
  };

  const openFileLocation = () => {
    if (selectedFile && globalDirectory) {
      window.electronAPI.openFileLocation(globalDirectory + '/' + selectedFile);
    }
  }

  return (
    <>
      <div className='toolbar-container scrollable light-bg'>
        <div className='toolbar-section'>
          EDIT
          <div className='toolbar-subsection'>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => callOp('handleCopy')}><Tooltip text="Copy"/><Copy size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => callOp('handleCut')}><Tooltip text="Cut"/><Scissors size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!clipboardFile ? ' grayed' : '')} onClick={() => callOp('handlePaste')}><Tooltip text="Paste"/><Clipboard size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => callOp('handleDuplicate')}><Tooltip text="Duplicate"/><CopyPlus size={iconSize}/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          SHARE / EXPORT
          <div className='toolbar-subsection'>
            <button className={'icon-button tooltip grayed'}><Tooltip text="Collaborate (Coming Soon)"/><Users size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')}><Tooltip text="Export to MuseScore"/><img src={mscz} color={"#737373"} alt="mscz icon" width={iconSize} height={iconSize} /></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')}><Tooltip text="Export to Audio"/><FileAudio2 size={iconSize}/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          FILE
          <div className='toolbar-subsection'>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')}><Tooltip text="Password Protect this File"/><KeyRound size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')}><Tooltip text="Tag this File"/><Tag size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={openFileLocation}><Tooltip text="Open File Location"/><FolderOpen size={iconSize}/></button>
            <button className={'icon-button tooltip' + (!selectedFile ? ' grayed' : '')} onClick={() => setShowDeleteConfirm(true)}><Tooltip text="Delete"/><Trash2 size={iconSize} color='#E46767'/></button>
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
        <DeleteConfirmationModal onComplete={() => { setShowDeleteConfirm(false); callOp('handleDelete') }} action={'Delete'} modifier={'Symphony'} />
      </GenericModal>
    </>
  );
}

export default Toolbar;