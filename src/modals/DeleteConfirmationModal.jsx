// NewFolder.js
import React, { useState, useEffect } from 'react';

//console.log('electronAPI:', window.electronAPI);

function DeleteConfirmationModal({onComplete, action='Delete', modifier='Object'}) {

  return (
    <>
      <div className='modal-title' text-style='display' style={{marginBottom : '15px'}}>Confirm</div>
      <div className='modal-paragraph'>Are you sure you want to {action.toLowerCase()} this {modifier}? This action cannot be undone.</div>
      <button className={'call-to-action-2'} text-style='display' onClick={() => onComplete()}>{action}</button>
    </>
  );
}

export default DeleteConfirmationModal;
