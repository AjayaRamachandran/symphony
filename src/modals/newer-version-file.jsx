import React from "react";
import { ExternalLink } from "lucide-react";

function NewerVersionFile({ onComplete, onClose }) {
  return (
    <>
      <div
        className="modal-title"
        style={{ marginBottom: "15px" }}
      >
        Unable to Open File
      </div>
      <div className="modal-paragraph" style={{ marginBottom: "10px" }}>
        This file was created in a newer version of Symphony. Get the latest
        version at symphony.nimbial.com to open it.
      </div>
      <div style={{ display: "flex", justifyContent: "right" }}>
        <button
          className={"call-to-action-2 gray"}
          onClick={() => onClose()}
        >
          Not now
        </button>
        <button
          className={"call-to-action-2"}
          style={{ marginLeft: "10px" }}
          onClick={() => onComplete()}
        >
          Go to Downloads
          <ExternalLink size={16} strokeWidth={2} />
        </button>
      </div>
    </>
  );
}

export default NewerVersionFile;
