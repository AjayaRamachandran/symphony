import React, { useState, useEffect } from "react";
import {
  ChartNoAxesGantt,
  Music,
  Save,
  Trash2,
  Check,
} from "lucide-react";

import Field from "@/ui/Field";
import Dropdown from "@/ui/Dropdown";
import SelectFile from "@/ui/SelectFile";
import { useDirectory } from "@/contexts/DirectoryContext";

const options = [
  { label: "Projects", icon: ChartNoAxesGantt },
  { label: "Exports", icon: Music },
  { label: "Symphony Auto-Save", icon: Save },
];

function EditModal({
  getParams,
  onClose,
  onRemove,
  onConfirm,
  onDeny,
  onRefresh,
  onComplete,
}) {
  const [sourceLocation, setSourceLocation] = useState("");
  const [destination, setDestination] = useState("");
  const [projectName, setProjectName] = useState("");
  const { setGlobalDirectory, selectedFile } = useDirectory();
  const [params, setParams] = useState({});
  const [settingsShowDelete, setSettingsShowDelete] = useState(true);

  useEffect(() => {
    window.electronAPI.getUserSettings().then((result) => {
      setSettingsShowDelete(!result["disable_delete_confirm"]);
    });
  }, [selectedFile]);

  useEffect(() => {
    getParams().then((result) => {
      setParams(result);
      const params = result;
      if (params.dest && destination === "") {
        setDestination(params.dest);
      }
      if (params.dir && sourceLocation === "") {
        setSourceLocation(params.dir);
      }
      if (params.name && projectName === "") {
        setProjectName(params.name);
      }
      console.log(result);
    });
  }, []);

  const selectedOption =
    options.find((opt) => opt.label === destination) || null;

  const openFolderDialog = async () => {
    console.log("button clicked");
    const result = await window.electronAPI.openDirectory();
    console.log("Dialog result:" + result);
    if (result) {
      setSourceLocation(result);
      const normalized = path.normalize(result);
      const parts = path.parse(normalized).dir.split(path.sep).filter(Boolean);
      setProjectName(parts[parts.length - 1]);
    }
  };

  const handleSelect = (selected) => {
    // selected is an object containing a label and an icon.
    setDestination(selected.label);
    //alert(`Selected: ${selected.label}`);
  };

  const changeFields = async () => {
    let exists = await window.electronAPI.checkIfExists({
      destination,
      projectName,
      sourceLocation,
    });
    exists = exists.success;
    console.log(`Exists: ${exists}`);
    let result = {};
    let sendRequest = {};
    if (exists) {
      sendRequest = {
        destination: params.dest,
        projectName: params.name,
        sourceLocation: params.dir,
      };
    } else {
      sendRequest = {
        destination: destination,
        projectName: projectName,
        sourceLocation: sourceLocation,
      };
    }
    result = await window.electronAPI.saveDirectory(sendRequest);

    if (result.success) {
      console.log(`Directory added: ${JSON.stringify(sendRequest)}`);
      setGlobalDirectory(
        exists ? params.dest : sourceLocation.replace(/\\/g, "/"),
      );

      if (!exists) {
        onClose();
      } else {
        onDeny();
      }

      onRefresh();
    } else {
      if (result.errorType === 409) {
        console.log(`Conflict: ${result.error}`);
        //onConflict();
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
        Edit Folder
      </div>
      <div className="modal-body">System File Location</div>
      <SelectFile selectedPath={sourceLocation} onClick={openFolderDialog} />
      <div className="modal-body" style={{ marginTop: "2em" }}>
        Folder Alias
      </div>
      <Field
        style={{ fontSize: "13px", width: "320px" }}
        value={projectName}
        onChange={(e) => setProjectName(e.target.value)}
        singleLine={true}
      />
      <div className="modal-body" style={{ marginTop: "2em" }}>
        Destination
      </div>
      <Dropdown
        options={options}
        onSelect={handleSelect}
        value={selectedOption}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          marginTop: "10px",
        }}
      >
        <button
          className={"call-to-action-2 red"}
          style={{ marginLeft: 0 }}
          onClick={settingsShowDelete ? onConfirm : onComplete}
        >
          <Trash2 size={16} />
          Remove
        </button>
        <button
          className={
            "call-to-action-2 green" +
            (params.dir !== sourceLocation ||
              params.dest !== destination ||
              params.name !== projectName
              ? ""
              : " locked")
          }
          style={{ marginLeft: 0 }}
          onClick={
            params.dir !== sourceLocation ||
              params.dest !== destination ||
              params.name !== projectName
              ? async () => {
                onRemove();
                await changeFields();
              }
              : undefined
          }
        >
          <Check size={16} />
          Save Changes
        </button>
      </div>
    </>
  );
}

export default EditModal;
