import React, { useState, useEffect } from "react";
import { ExternalLink } from "lucide-react";

function NewVersionAvailable({ onComplete, onClose, version }) {
  return (
    <>
      <div
        className="modal-title"
        style={{ marginBottom: "15px" }}
      >
        Symphony v{version} is available!
      </div>
      <div className="modal-paragraph" style={{ marginBottom: "10px" }}>
        You're behind the latest version. Upgrade to get access to the latest features.
      </div>
      <div style={{ display: "flex", justifyContent: "right" }}>
        <button
          className={"call-to-action-2 gray"}
          onClick={() => onClose()}
        >
          I'll miss out
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

export default NewVersionAvailable;
