import React, { useState, useEffect } from "react";
import { Plus } from "lucide-react";
import path from "path-browserify";

import fileIcon from "@/assets/file-icon.svg";
import wavIcon from "@/assets/wav-icon.svg";
import mp3Icon from "@/assets/mp3-icon.svg";
import midiIcon from "@/assets/midi-icon.svg";
import { useDirectory } from "@/contexts/DirectoryContext";

import "./file.css";

const fileTypeMap = {
  ".symphony": {
    icon: fileIcon,
    label: "SYMPHONY File",
  },
  ".wav": {
    icon: wavIcon,
    label: "WAV Lossless Audio File",
  },
  ".mp3": {
    icon: mp3Icon,
    label: "MP3 Compressed Audio File",
  },
  ".mid": {
    icon: midiIcon,
    label: "Musical Instrument Digital Interface (MIDI) File",
  },
};

function File({ name }) {
  const {
    globalDirectory,
    selectedFile,
    setSelectedFile,
    clipboardFile,
    clipboardCut,
    setGlobalUpdateTimestamp,
    globalUpdateTimestamp,
    viewType,
    tempFileName,
    globalStars,
  } = useDirectory();

  const [fileName, setFileName] = useState(name);
  const [displayName, setDisplayName] = useState(fileName);
  const [isStarred, setIsStarred] = useState(false);

  const runProcessCommand = async (title) => {
    console.log(title);
    setGlobalUpdateTimestamp(Date.now);
    const result = await window.electronAPI.doProcessCommand(
      path.join(globalDirectory, `${title}`),
      "open"
    );
    console.log(result);
  };

  useEffect(() => {
    setFileName(name);
  }, [selectedFile, name]);

  useEffect(() => {
    if (globalDirectory) {
      const fullPath = path.join(globalDirectory, fileName).replace(/\\/g, "/");
      setIsStarred(globalStars.includes(fullPath));
    }
  }, [globalStars, fileName, globalDirectory]);

  useEffect(() => {
    setDisplayName(
      selectedFile === name &&
        selectedFile.endsWith(".symphony") &&
        tempFileName
        ? tempFileName + ".symphony"
        : fileName
    );
  }, [name, tempFileName, fileName, selectedFile]);

  // 🔍 Find the file type dynamically
  const fileType = Object.entries(fileTypeMap).find(([ext]) =>
    displayName.toLowerCase().endsWith(ext)
  )?.[1] || {
    icon: fileIcon,
    label: "Unknown File Type",
  };

  return (
    <>
      <button
        className={
          "file-select-box" +
          (viewType === "grid"
            ? ""
            : viewType === "content"
            ? "-content"
            : "-list") +
          (selectedFile === fileName ? " highlighted" : "")
        }
        style={{
          opacity:
            clipboardFile &&
            path.basename(clipboardFile) === fileName &&
            clipboardCut
              ? 0.6
              : 1,
        }}
        draggable
        onDragStart={(e) => {
          e.preventDefault();
          const filePath = path
            .join(globalDirectory, displayName)
            .replace(/\\/g, "/");
          console.log("Dragging file:", filePath);
          window.electronAPI.startFileDrag(filePath);
        }}
        onClick={(e) => {
          e.stopPropagation();
          setSelectedFile(fileName);
          console.log(fileName);
        }}
        onDoubleClick={async () => {
          if (displayName.endsWith(".symphony")) {
            runProcessCommand(selectedFile);
          } else {
            await window.electronAPI.openNativeApp(
              path.join(globalDirectory, displayName)
            );
            setGlobalUpdateTimestamp(Date.now());
          }
        }}
      >
        <img
          src={fileType.icon}
          alt="File icon"
          color="#606060"
          height={viewType === "grid" ? 78 : viewType === "content" ? 55 : 21}
          style={{ marginTop: viewType === "list" ? "3px" : "0" }}
        />
        <div
          style={{
            display: "flex",
            flexDirection: viewType === "content" ? "column" : "row",
          }}
        >
          <span
            style={{
              display: "block",
              width: "100%",
              textAlign: viewType === "grid" ? "center" : "left",
              fontSize: "1em",
              marginTop: viewType === "grid" ? "1px" : "2px",
              wordBreak: "break-word",
              overflowWrap: "break-word",
              whiteSpace: "normal",
            }}
          >
            {displayName}
            {isStarred && (
              <i
                className="bi bi-star-fill"
                style={{
                  margin: "0px 4px",
                  fontSize: "10px",
                  color: "#b8a463",
                }}
              ></i>
            )}
          </span>
          {viewType === "grid" ? null : viewType === "content" ? (
            <span style={{ opacity: 0.5, fontSize: "0.8em", marginTop: "7px" }}>
              {fileType.label}
            </span>
          ) : (
            <span
              style={{
                opacity: 0.5,
                fontSize: "1em",
                marginTop: "3px",
                width: "100%",
              }}
            >
              {fileType.label}
            </span>
          )}
        </div>
      </button>
    </>
  );
}

export default File;
