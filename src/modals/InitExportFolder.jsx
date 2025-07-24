import React, { useState, useEffect } from 'react';

function InitExportFolder({onComplete}) {

  return (
    <>
      <div className='modal-title' text-style='display' style={{marginBottom : '15px'}}>Missing Export Folder</div>
      <div className='modal-paragraph'>To create an export, you'll need to create an export folder first.</div>
      
    </>
  );
}

export default InitExportFolder;