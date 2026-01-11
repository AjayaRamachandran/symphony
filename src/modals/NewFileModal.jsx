// NewFolder.js
import React, { useState, useEffect } from "react";
import { Plus } from "lucide-react";

import Field from "@/components/content-components/right-panel-components/Field";
import Dropdown from "@/components/Dropdown";
import Tooltip from "@/components/Tooltip";

const phrases = [
  "Ex: My Amazing Masterpiece",
  "Ex: My World-Class Composition",
  "Ex: My Magnum Opus",
  "Ex: My Symphony of Dreams",
  "Ex: My Harmonic Triumph",
  "Ex: My Celestial Soundscape",
  "Ex: My Chart-Topping Creation",
  "Ex: My Award-Winning Arrangement",
  "Ex: My Serenade to the Stars",
];

function NewFileModal({ onClose }) {
  const [projectName, setProjectName] = useState("");
  const [defaultText, setDefaultText] = useState("");

  useEffect(() => {
    setDefaultText(phrases[Math.floor(Math.random() * phrases.length)]);
  }, []);

  return (
    <>
      <div
        className="modal-title"
        text-style="display"
        style={{ marginBottom: "25px" }}
      >
        Create New Symphony
      </div>
      <div className="modal-paragraph">
        Give your symphony a name. You can always change this later.
      </div>
      <Field
        fontSize={"13px"}
        value={projectName}
        defaultText={defaultText}
        onChange={(e) => setProjectName(e.target.value)}
      />
      <button
        className={
          projectName == "" ? "call-to-action-2 locked" : "call-to-action-2"
        }
        text-style="display"
        onClick={() => onClose(projectName)}
      >
        Create
      </button>
    </>
  );
}

export default NewFileModal;
