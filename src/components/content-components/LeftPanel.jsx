import React, { useState, useEffect } from 'react';
import Directory from './left-panel-components/Directory';

import "./left-panel.css";

function LeftPanel() {

  return (
    <>
      <div className="content-panel-container">
        <div className='big-title' textStyle='display'>
          Home
        </div>
        <div className='section-title'>
          DIRECTORY
        </div>
        <Directory />
        <div className='section-title'>
          RECENTLY VIEWED
        </div>
        <Directory />
      </div>
    </>
  );
}

export default LeftPanel;