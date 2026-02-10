import React, { useState, useEffect } from "react";

import {
  FolderOpen,
  ChartNoAxesGantt,
  Music,
  Save,
  AudioLines,
  FolderClosed,
  KeyboardMusic,
  FileMusic,
} from "lucide-react";
import path from "path-browserify";

import Field from "@/ui/Field";
import Dropdown from "@/ui/Dropdown";
import Tooltip from "@/ui/Tooltip";
import { useDirectory } from "@/contexts/DirectoryContext";
import InitExportFolder from "@/modals/InitExportFolder";

const formats = [
  { label: "MIDI", icon: KeyboardMusic },
  { label: "MusicXML", icon: FileMusic },
];

function ConvertModal({ onClose, onComplete }) {
  const [projectName, setProjectName] = useState(" ");
  const [destination, setDestination] = useState(null);
  const [format, setFormat] = useState(null);
  const [folders, setFolders] = useState([]);
  const [showInitExportFolder, setShowInitExportFolder] = useState(false);

  const { globalDirectory, setGlobalDirectory, selectedFile, setSelectedFile } =
    useDirectory();

  useEffect(() => {
    window.electronAPI.getDirectory().then((result) => {
      const rawExports = result["Exports"];
      const formatted = rawExports.map((obj) => {
        const [label, value] = Object.entries(obj)[0];
        return {
          label: `${label}`,
          value,
          icon: FolderClosed,
        };
      });
      setFolders(formatted);
      console.log(formatted);
      if (formatted.length === 0) {
        setShowInitExportFolder(true);
      }
    });
  }, []);

  const selectedFormat = formats.find((opt) => opt.label === format) || null;
  const selectedFolder =
    folders.find((opt) => opt.label === destination) || null;

  const handleSelect = (selected, setAttr) => {
    setAttr(selected.label);
  };

  const finish = async (pathToFile) => {
    document.body.style.cursor = "wait";
    try {
      await window.electronAPI.doProcessCommand(
        path.join(globalDirectory, path.basename(selectedFile)),
        "convert",
        { dest_folder_path: selectedFolder.value, file_type: format.toLowerCase() },
      );
    } finally {
      document.body.style.cursor = "default";
    }
  };

  return (
    <>
      {showInitExportFolder ? (
        <>
          <InitExportFolder
            onComplete={() => {
              setShowInitExportFolder(false);
              onClose();
            }}
          />
        </>
      ) : (
        <>
          <div
            className="modal-title"
            text-style="display"
            style={{ marginBottom: "25px" }}
          >
            Convert to...
          </div>
          <div className="modal-body">Symphony Name</div>
          <div>
            <div
              className="modal-file-explorer-button"
              style={{ cursor: "not-allowed" }}
            >
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
                {selectedFile.slice(0, -9)}
              </span>
            </div>
          </div>
          <div className="modal-body" style={{ marginTop: "2em" }}>
            Destination
          </div>
          <Dropdown
            options={folders}
            onSelect={(e) => handleSelect(e, setDestination)}
            value={selectedFolder}
          />
          <div className="modal-body" style={{ marginTop: "2em" }}>
            Format
          </div>
          <Dropdown
            options={formats}
            onSelect={(e) => handleSelect(e, setFormat)}
            value={selectedFormat}
          />
          <button
            className={
              format === "" || destination === "" || projectName === ""
                ? "call-to-action-2 locked"
                : "call-to-action-2"
            }
            text-style="display"
            onClick={
              format === "" || destination === "" || projectName === ""
                ? null
                : async () => {
                    await finish(selectedFolder.value);
                    setGlobalDirectory(selectedFolder.value);
                    setSelectedFile(null);
                    onClose();
                  }
            }
          >
            Export
          </button>
        </>
      )}
    </>
  );
}

export default ConvertModal;
