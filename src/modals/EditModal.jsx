import React, { useState, useEffect } from "react";
import {
  FolderOpen,
  ChartNoAxesGantt,
  Music,
  Save,
  Trash2,
  Check,
} from "lucide-react";

import Field from "@/ui/Field";
import Dropdown from "@/ui/Dropdown";
import Tooltip from "@/ui/Tooltip";
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
        text-style="display"
        style={{ marginBottom: "25px" }}
      >
        Edit Folder
      </div>
      <div className="modal-body">System File Location</div>
      {sourceLocation != "" ? (
        <Tooltip text={`${sourceLocation}  ⦁  Click to Change`}>
          <button
            className="modal-file-explorer-button"
            onClick={openFolderDialog}
          >
            <FolderOpen
              size={16}
              style={{ marginRight: "8px", flexShrink: 0 }}
            />
            <span
              style={{
                overflow: "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
                display: "inline-block",
                flexGrow: 1,
                minWidth: 0,
              }}
            >
              {sourceLocation == "" ? "Open File Explorer..." : sourceLocation}
            </span>
          </button>
        </Tooltip>
      ) : (
        <button
          className="modal-file-explorer-button"
          onClick={openFolderDialog}
        >
          <FolderOpen size={16} style={{ marginRight: "8px", flexShrink: 0 }} />
          <span
            style={{
              overflow: "hidden",
              whiteSpace: "nowrap",
              textOverflow: "ellipsis",
              display: "inline-block",
              flexGrow: 1,
              minWidth: 0,
            }}
          >
            Open File Explorer...
          </span>
        </button>
      )}
      <div className="modal-body" style={{ marginTop: "2em" }}>
        Folder Alias
      </div>
      <Field
        fontSize={"13px"}
        value={projectName}
        onChange={(e) => setProjectName(e.target.value)}
        singleLine={true}
        width={"320px"}
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
          text-style="display"
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
          text-style="display"
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
