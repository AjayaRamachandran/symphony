import React, { useState, useEffect } from "react";


function GUIAlreadyRunning({ onComplete }) {
  return (
    <>
      <div
        className="modal-title"
        style={{ marginBottom: "15px" }}
      >
        Unable to Open File
      </div>
      <div className="modal-paragraph">
        Another Symphony file is currently open. Close the active file to continue.
      </div>
      <button
        className={"call-to-action-2"}
        onClick={() => onComplete()}
      >
        Got it
      </button>
    </>
  );
}

export default GUIAlreadyRunning;
