import React, { useState, useEffect } from "react";

import Search from "@/components/content-components/center-panel-components/search-bar";
import Toolbar from "@/components/content-components/center-panel-components/toolbar";
import Files from "@/components/content-components/center-panel-components/files";

function CenterPanel() {
  return (
    <>
      <div className="content-nopanel-container">
        <Search />
        <Toolbar />
        <Files />
        {/*<SelectionInfo /> */}
      </div>
    </>
  );
}

export default CenterPanel;
