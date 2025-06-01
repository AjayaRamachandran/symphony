import React, { useState, useEffect } from 'react';
import LeftPanel from "./content-components/LeftPanel";
import RightPanel from "./content-components/RightPanel";

function Content() {

  return (
    <>
      <LeftPanel />

      <RightPanel />
    </>
  );
}

export default Content;
