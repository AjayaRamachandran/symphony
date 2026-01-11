import React, { useState, useEffect } from "react";

function InvalidDrop({ onComplete }) {
  return (
    <>
      <div
        className="modal-title"
        text-style="display"
        style={{ marginBottom: "15px" }}
      >
        Invalid Drop
      </div>
      <div className="modal-paragraph">
        Symphony only allows drag-and-drop for .symphony and .wav files.
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

export default InvalidDrop;
