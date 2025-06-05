import React, { useState, useEffect } from 'react';

import LeftPanel from "./content-components/LeftPanel";
import RightPanel from "./content-components/RightPanel";

import "./content.css"

function Content() {

  return (
    <>
      <div className='content'>
        <LeftPanel />

        <RightPanel />
      </div>
    </>
  );
}

export default Content;
