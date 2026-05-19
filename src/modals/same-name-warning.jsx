import React, { useState, useEffect } from "react";


function SameNameWarning({ onComplete }) {
  return (
    <>
      <div
        className="modal-title"
        style={{ marginBottom: "15px" }}
      >
        Conflict
      </div>
      <div className="modal-paragraph">
        A folder with this alias or file location already exists. Please use a
        unique alias and file location.
      </div>
      <button
        className={"call-to-action-2"}
        onClick={() => onComplete()}
      >
        Okay
      </button>
    </>
  );
}

export default SameNameWarning;
