import React, { useState, useEffect } from 'react';

import LeftPanel from "./content-components/LeftPanel";
import CenterPanel from "./content-components/CenterPanel";
import RightPanel from "./content-components/RightPanel";

import "./content.css"

function Content() {

  return (
    <>
      <div className='content scrollable'>
        <LeftPanel />
        <CenterPanel />
        <RightPanel />
      </div>
    </>
  );
}

export default Content;
