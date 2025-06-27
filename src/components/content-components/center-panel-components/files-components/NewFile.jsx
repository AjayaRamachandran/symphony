import React, { useState } from 'react';
import { Plus } from 'lucide-react';

import "./new-file.css";

function NewFile() {

  return (
    <>
      <button className='file-select-box'>
        <div className='rounded-rect-icon'><Plus size={40} color='#606060'/></div>
        New Symphony
      </button>
    </>
  );
}

export default NewFile;