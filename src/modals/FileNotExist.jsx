import React, { useState, useEffect } from "react";


function FileNotExist({ onComplete, fileName = () => "" }) {
  return (
    <>
      <div
        className="modal-title"
        text-style="display"
        style={{ marginBottom: "15px" }}
      >
        File Does Not Exist
      </div>
      <div className="modal-paragraph">
        There was an error trying to open {fileName() || "the file"}. This file
        may have been moved or deleted.
      </div>
      <button
        className={"call-to-action-2"}
        text-style="display"
        onClick={() => onComplete()}
      >
        Okay
      </button>
    </>
  );
}

export default FileNotExist;
