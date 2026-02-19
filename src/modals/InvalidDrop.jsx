import React, { useState, useEffect } from "react";


function InvalidDrop({ onComplete }) {
  return (
    <>
      <div
        className="modal-title"

        style={{ marginBottom: "15px" }}
      >
        Invalid Drop
      </div>
      <div className="modal-paragraph">
        Symphony only allows drag-and-drop for .symphony and .wav files.
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

export default InvalidDrop;
