import React, { useState, useEffect } from 'react';

function SameNameWarning({onComplete}) {

  return (
    <>
      <div className='modal-title' text-style='display' style={{marginBottom : '15px'}}>Conflict</div>
      <div className='modal-paragraph'>A folder with this alias or file location already exists. Please use a unique alias and file location.</div>
      <button className={'call-to-action-2'} text-style='display' onClick={() => onComplete()}>Okay</button>
    </>
  );
}

export default SameNameWarning;