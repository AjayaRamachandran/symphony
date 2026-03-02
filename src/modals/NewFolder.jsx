import React, { useState, useEffect } from "react";
import { ChartNoAxesGantt, Music, Save } from "lucide-react";
import path from "path-browserify";

import Field from "@/ui/Field";
import Dropdown from "@/ui/Dropdown";
import SelectFile from "@/ui/SelectFile";
import { useDirectory } from "@/contexts/DirectoryContext";

const options = [
  { label: "Projects", icon: ChartNoAxesGantt },
  { label: "Exports", icon: Music },
  { label: "Symphony Auto-Save", icon: Save },
];

function NewFolder({ defaultDestProp = "", onClose, onConflict }) {
  const [sourceLocation, setSourceLocation] = useState("");
  const [destination, setDestination] = useState("");
  const [projectName, setProjectName] = useState("");
  const { globalDirectory, setGlobalDirectory } = useDirectory();

  useEffect(() => {
    if (defaultDestProp && destination === "") {
      setDestination(defaultDestProp);
      console.log(`defaultDestProp was set to ${defaultDestProp}`);
    }
  }, [defaultDestProp]);

  const selectedOption =
    options.find((opt) => opt.label === destination) || null;

  const openFolderDialog = async () => {
    console.log("button clicked");
    const result = await window.electronAPI.openDirectory();
    console.log("Dialog result:" + result);
    if (result) {
      setSourceLocation(result);
      setProjectName(path.basename(result.replace(/\\/g, "/")));
    }
  };

  const handleSelect = (selected) => {
    // selected is an object containing a label and an icon.
    setDestination(selected.label);
    //alert(`Selected: ${selected.label}`);
  };

  const addDirectory = async () => {
    const result = await window.electronAPI.saveDirectory({
      destination,
      projectName,
      sourceLocation,
    });

    if (result.success) {
      console.log(
        `Directory added: ${[projectName, destination, sourceLocation]}`,
      );
      setGlobalDirectory(sourceLocation);
      onClose();
    } else {
      if (result.errorType === 409) {
        console.log(`Conflict: ${result.error}`);
        onConflict();
      } else {
        alert("Error: " + result.error);
      }
    }
  };

  return (
    <>
      <div
        className="modal-title"
        style={{ marginBottom: "25px" }}
      >
        Add New Folder
      </div>
      <div className="modal-body">System File Location</div>
      <SelectFile selectedPath={sourceLocation} onClick={openFolderDialog} />
      <div className="modal-body" style={{ marginTop: "2em" }}>
        Folder Alias
      </div>
      <Field
        style={{ fontSize: "13px" }}
        value={projectName}
        onChange={(e) => setProjectName(e.target.value)}
      />
      <div className="modal-body" style={{ marginTop: "2em" }}>
        Destination
      </div>
      <Dropdown
        options={options}
        onSelect={handleSelect}
        value={selectedOption}
      />
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
        Add
      </button>
    </>
  );
}

export default NewFolder;
