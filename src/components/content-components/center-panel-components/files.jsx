import React, { useState, useEffect, useCallback } from "react";

import { useDirectory } from "@/contexts/directory-context";
import {
  isSupportedDropExtension,
  getFileName,
  moveInAppFileToDirectory,
} from "@/utils/move-in-app-file";

import "@/components/universal-styling/files.css";
import NewFile from "@/components/content-components/center-panel-components/files-components/new-file";
import File from "@/components/content-components/center-panel-components/files-components/file";

import InvalidDrop from "@/modals/invalid-drop";
import GenericModal from "@/modals/generic-modal";

function Files() {
  const {
    globalDirectory,
    globalUpdateTimestamp,
    setGlobalUpdateTimestamp,
    selectedFile,
    setSelectedFile,
    viewType,
    setGlobalStars,
    globalStars,
    draggingFilePath,
    setDraggingFilePath,
  } = useDirectory();

  const [symphonyFiles, setSymphonyFiles] = useState([]);
  const [currentSectionType, setCurrentSectionType] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showInvalidModal, setShowInvalidModal] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setGlobalUpdateTimestamp(Date.now());
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleInvalidDrop = () => setShowInvalidModal(true);
    window.addEventListener("symphony:invalid-drop", handleInvalidDrop);
    return () =>
      window.removeEventListener("symphony:invalid-drop", handleInvalidDrop);
  }, []);

  useEffect(() => {
    if (!globalDirectory) {
      setSymphonyFiles("not a valid dir");
      setCurrentSectionType("");
      return;
    }

    window.electronAPI.getSymphonyFiles(globalDirectory).then((files) => {
      setSymphonyFiles(files);
    });

    window.electronAPI.getSectionForPath(globalDirectory).then((type) => {
      setCurrentSectionType(type.section);
    });

    // Fetch all starred files once for this directory
    window.electronAPI.getStars().then((stars) => {
      const normalizedStars = stars.map((s) => s.replace(/\\/g, "/"));
      setGlobalStars(normalizedStars);
    });
  }, [globalDirectory, globalUpdateTimestamp]);

  const handleDrop = useCallback(
    async (e) => {
      e.preventDefault();
      setIsDragging(false);

      const fileCount = e.dataTransfer?.files?.length ?? 0;
      console.log("[symphony-drag] Files.handleDrop", {
        draggingFilePath,
        globalDirectory,
        fileCount,
        types: e.dataTransfer ? Array.from(e.dataTransfer.types) : null,
        lastNativeDrop: window.__symphonyLastNativeDrop || 0,
      });

      // A native OS drop on Windows fires through the host IDropTarget and
      // dispatches ``symphony:native-drop`` separately. Skip the HTML5 path
      // briefly so the same gesture is not handled twice.
      const lastNative = window.__symphonyLastNativeDrop || 0;
      if (Date.now() - lastNative < 400) {
        console.log("[symphony-drag] Files.handleDrop: debounced post-native");
        return;
      }

      // In-app drag has no real File entries; resolve by source path instead.
      if (draggingFilePath) {
        const fileName = getFileName(draggingFilePath);
        if (!isSupportedDropExtension(fileName)) {
          setShowInvalidModal(true);
        } else {
          const result = await moveInAppFileToDirectory(
            draggingFilePath,
            globalDirectory,
          );
          if (result.status === "invalid") {
            setShowInvalidModal(true);
          }
          setDraggingFilePath(null);
          setGlobalUpdateTimestamp(Date.now());
        }
        return;
      }

      const files = Array.from(e.dataTransfer.files);
      const droppedFiles = files.filter((file) =>
        isSupportedDropExtension(file.name),
      );

      if (droppedFiles.length === 0) {
        setShowInvalidModal(true);
      }

      droppedFiles.forEach(async (file) => {
        try {
          const arrayBuffer = await file.arrayBuffer();
          await window.electronAPI.moveFileRaw(
            arrayBuffer,
            file.name,
            globalDirectory,
            file.path,
          );
          setGlobalUpdateTimestamp(Date.now());
        } catch (err) {
          console.error("Error processing dropped file:", err);
        }
      });
    },
    [
      globalDirectory,
      draggingFilePath,
      setDraggingFilePath,
      setGlobalUpdateTimestamp,
    ],
  );

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = draggingFilePath ? "move" : "copy";
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  return (
    <>
      {symphonyFiles === "not a valid dir" ? (
        <div className="empty-box">No Folder Selected</div>
      ) : null}
      {symphonyFiles === "no files" ? null : (
        <div
          className="files scrollable dark-bg"
          data-drop-folder={globalDirectory || ""}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedFile(null);
          }}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          style={{
            outline: isDragging ? "1px dashed var(--muted-foreground)" : "none",
            filter: isDragging ? "brightness(1.1)" : "none",
          }}
        >
          {currentSectionType === "Projects" && <NewFile />}
          {Array.isArray(symphonyFiles) &&
            symphonyFiles.map((fileName, idx) => (
              <File key={idx} name={fileName} />
            ))}
        </div>
      )}
      <GenericModal
        isOpen={showInvalidModal}
        onClose={() => {
          setShowInvalidModal(false);
        }}
      >
        <InvalidDrop onComplete={() => setShowInvalidModal(false)} />
      </GenericModal>
    </>
  );
}

export default Files;
