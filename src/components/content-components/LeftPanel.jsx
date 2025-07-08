import React, { useState, useEffect } from 'react';
import Directory from './left-panel-components/Directory';
import RecentlyViewed from './left-panel-components/RecentlyViewed';

import "./left-panel.css";

function LeftPanel() {

  return (
    <>
      <div className="content-panel-container">
        <div className='big-title' text-style='display'>
          Home
        </div>
        <div className='section-title'>
          DIRECTORY
        </div>
        <Directory />
        <div className='section-title'>
          RECENTLY LAUNCHED
        </div>
        <RecentlyViewed />
      </div>
    </>
  );
}

export default LeftPanel;