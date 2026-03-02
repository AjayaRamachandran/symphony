import React, { useState, useEffect } from "react";
import SelectFile from "@/ui/SelectFile";

function AddAutoSave({ onClose }) {
  const [sourceLocation, setSourceLocation] = useState("");
  const destination = "Symphony Auto-Save";
  const projectName = "Auto-Save";

  const openFolderDialog = async () => {
    console.log("button clicked");
    const result = await window.electronAPI.openDirectory();
    console.log("Dialog result:" + result);
    if (result) {
      setSourceLocation(result);
    }
  };

  const addDirectory = async () => {
    const result = await window.electronAPI.saveDirectory({
      destination: destination,
      projectName: projectName,
      sourceLocation: sourceLocation,
    });
    if (result.success) {
      console.log(
        `Directory added: ${[projectName, destination, sourceLocation]}`,
      );
      // Optionally reset fields or close modal
    } else {
      alert("Error: " + result.error);
    }
    onClose();
  };

  return (
    <>
      <div className="modal-title" >
        Set Up Auto-Save
      </div>
      <div className="modal-paragraph">
        Let's choose a destination for your Auto-Save files so you can easily
        recover your work if needed.
      </div>
      <SelectFile selectedPath={sourceLocation} onClick={openFolderDialog} />
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div className="modal-whisper">You can change this at any time.</div>
        <button
          className={
            sourceLocation == "" || destination == "" || projectName == ""
              ? "call-to-action-2 locked"
              : "call-to-action-2"
          }
          onClick={
            sourceLocation == "" || destination == "" || projectName == ""
              ? null
              : addDirectory
          }
        >
          Done
        </button>
      </div>
    </>
  );
}

export default AddAutoSave;
