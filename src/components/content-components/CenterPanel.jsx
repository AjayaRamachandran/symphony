import React, { useState, useEffect } from 'react';

import Search from './center-panel-components/SearchBar'
import Toolbar from './center-panel-components/Toolbar'

import "./center-panel.css";

function CenterPanel() {

  return (
    <>
      <div className="content-nopanel-container">
        <Search />
        <Toolbar />
        {/*<Files />
        <SelectionInfo /> */}
      </div>
    </>
  );
}

export default CenterPanel;