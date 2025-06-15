import React, { useState, useEffect } from 'react';
import { Copy, Scissors, Clipboard, CopyPlus, Users, KeyRound, Tag, FolderOpen, Trash2, FileAudio2, Grid2x2, List, Rows2 } from 'lucide-react';

import mscz from '@/assets/mscz-icon.svg';
import Tooltip from '@/components/Tooltip';

import './toolbar.css'

function Toolbar() {

  return (
    <>
      <div className='toolbar-container scrollable'>
        <div className='toolbar-section'>
          EDIT
          <div className='toolbar-subsection'>
            <button className='icon-button tooltip'><Tooltip text="Copy"/><Copy size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="Cut"/><Scissors size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="Paste"/><Clipboard size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="Duplicate"/><CopyPlus size={18}/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          SHARE / EXPORT
          <div className='toolbar-subsection'>
            <button className='icon-button tooltip'><Tooltip text="Collaborate"/><Users size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="Export to MuseScore"/><img src={mscz} color="#606060" alt="mscz icon" width={18} height={18} /></button>
            <button className='icon-button tooltip'><Tooltip text="Export to Audio"/><FileAudio2 size={18}/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          FILE
          <div className='toolbar-subsection'>
            <button className='icon-button tooltip'><Tooltip text="Password Protect this File"/><KeyRound size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="Tag this File"/><Tag size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="Open File Location"/><FolderOpen size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="Delete"/><Trash2 size={18} color='#E46767'/></button>
          </div>
        </div>
        <hr />
        <div className='toolbar-section'>
          VIEW
          <div className='toolbar-subsection'>
            <button className='icon-button tooltip'><Tooltip text="Grid"/><Grid2x2 size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="List"/><List size={18}/></button>
            <button className='icon-button tooltip'><Tooltip text="Content"/><Rows2 size={18}/></button>
          </div>
        </div>
      </div>
    </>
  );
}

export default Toolbar;