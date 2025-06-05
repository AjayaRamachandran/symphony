import React, { useState, useEffect } from 'react';

import "./right-panel.css";

function RightPanel() {

  return (
    <>
      <div className="content-panel-container">
        <div className='med-title' textStyle='display'>
          Details
        </div>
        <div className='field-label'>
          Title
        </div>
      </div>
    </>
  );
}

export default RightPanel;