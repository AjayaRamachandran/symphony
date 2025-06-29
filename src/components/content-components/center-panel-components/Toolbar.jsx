import React, { useState, useEffect } from 'react';
import { Copy, Scissors, Clipboard, CopyPlus, Users, KeyRound, Tag, FolderOpen, Trash2, FileAudio2, LayoutGrid, List, Rows2 } from 'lucide-react';

import mscz from '@/assets/mscz-icon.svg';
import Tooltip from '@/components/Tooltip';

import './toolbar.css'
import { useDirectory } from '@/contexts/DirectoryContext';

function Toolbar() {
  const { viewType, setViewType } = useDirectory();
  const iconSize = 20

  return (
    <>
      <div className='toolbar-container scrollable light-bg'>
        <div className='toolbar-section'>
          EDIT
          <div className='toolbar-subsection'>
            <button className='icon-button tooltip'><Tooltip text="Copy"/><Copy size={iconSize}/></button>
            <button className='icon-button tooltip'><Tooltip text="Cut"/><Scissors size={iconSize}/></button>
            <button className='icon-button tooltip'><Tooltip text="Paste"/><Clipboard size={iconSize}/></button>
            <button className='icon-button tooltip'><Tooltip text="Duplicate"/><CopyPlus size={iconSize}/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          SHARE / EXPORT
          <div className='toolbar-subsection'>
            <button className='icon-button tooltip'><Tooltip text="Collaborate"/><Users size={iconSize}/></button>
            <button className='icon-button tooltip'><Tooltip text="Export to MuseScore"/><img src={mscz} color="#606060" alt="mscz icon" width={iconSize} height={iconSize} /></button>
            <button className='icon-button tooltip'><Tooltip text="Export to Audio"/><FileAudio2 size={iconSize}/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          FILE
          <div className='toolbar-subsection'>
            <button className='icon-button tooltip'><Tooltip text="Password Protect this File"/><KeyRound size={iconSize}/></button>
            <button className='icon-button tooltip'><Tooltip text="Tag this File"/><Tag size={iconSize}/></button>
            <button className='icon-button tooltip'><Tooltip text="Open File Location"/><FolderOpen size={iconSize}/></button>
            <button className='icon-button tooltip'><Tooltip text="Delete"/><Trash2 size={iconSize} color='#E46767'/></button>
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
    </>
  );
}

export default Toolbar;