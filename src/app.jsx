import React, { useEffect, useCallback } from "react";
import HomePage from "@/pages/home-page";
import PendingFileHandoff from "@/components/pending-file-handoff";
import { useDirectory } from "@/contexts/directory-context";
import path from "path-browserify";
import {
  isSupportedDropExtension,
  moveInAppFileToDirectory,
} from "@/utils/move-in-app-file";

function App() {
  const {
    selectedFile,
    globalDirectory,
    clipboardFile,
    setClipboardFile,
    clipboardCut,
    setClipboardCut,
    setGlobalUpdateTimestamp,
    draggingFilePath,
    setDraggingFilePath,
  } = useDirectory();

  // Operator functions
  const handleCopy = useCallback(() => {
    if (selectedFile && globalDirectory) {
      setClipboardFile(path.join(globalDirectory, selectedFile));
      setClipboardCut(false);
    }
  }, [selectedFile, globalDirectory, setClipboardFile, setClipboardCut]);

  const handleCut = useCallback(() => {
    if (selectedFile && globalDirectory) {
      setClipboardFile(path.join(globalDirectory, selectedFile));
      setClipboardCut(true);
    }
  }, [selectedFile, globalDirectory, setClipboardFile, setClipboardCut]);

  const handlePaste = useCallback(async () => {
    if (clipboardFile && globalDirectory) {
      const baseName = path.basename(clipboardFile);
      let destPath = path.join(globalDirectory, baseName);
      let finalDest = destPath;
      let counter = 1;
      while (await window.electronAPI.fileExists(finalDest)) {
        const ext = path.extname(baseName);
        const name = path.basename(baseName, ext);
        finalDest = path.join(
          globalDirectory,
          `${name} (copy${counter > 1 ? " " + counter : ""})${ext}`,
        );
        counter++;
      }
      await window.electronAPI.copyFile(clipboardFile, finalDest);
      setGlobalUpdateTimestamp(Date.now());
      if (clipboardCut) {
        await window.electronAPI.deleteFile(clipboardFile);
        setClipboardFile(null);
        setClipboardCut(false);
      }
    }
  }, [
    clipboardFile,
    clipboardCut,
    globalDirectory,
    setClipboardFile,
    setClipboardCut,
    setGlobalUpdateTimestamp,
  ]);

  const handleDuplicate = useCallback(async () => {
    if (selectedFile && globalDirectory) {
      const srcPath = path.join(globalDirectory, selectedFile);
      const baseName = path.basename(selectedFile);
      let destPath = path.join(globalDirectory, baseName);
      let finalDest = destPath;
      let counter = 1;
      while (await window.electronAPI.fileExists(finalDest)) {
        const ext = path.extname(baseName);
        const name = path.basename(baseName, ext);
        finalDest = path.join(
          globalDirectory,
          `${name} (copy${counter > 1 ? " " + counter : ""})${ext}`,
        );
        counter++;
      }
      await window.electronAPI.copyFile(srcPath, finalDest);
      setGlobalUpdateTimestamp(Date.now());
    }
  }, [selectedFile, globalDirectory, setGlobalUpdateTimestamp]);

  useEffect(() => {
    const handler = async (e) => {
      const isAccelKey = e.ctrlKey || e.metaKey;
      const target = e.target;
      const isEditingText =
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) ||
          Boolean(
            target.closest(
              '[contenteditable="true"], input, textarea, select, [role="textbox"]',
            ),
          ));

      if (e.key === "F12") {
        window.electronAPI.toggleDevTools();
      }
      if (!isEditingText && isAccelKey && e.key.toLowerCase() === "c")
        handleCopy();
      if (!isEditingText && isAccelKey && e.key.toLowerCase() === "x")
        handleCut();
      if (!isEditingText && isAccelKey && e.key.toLowerCase() === "v")
        await handlePaste();
      if (!isEditingText && isAccelKey && e.key.toLowerCase() === "d")
        await handleDuplicate();
      if (!isEditingText && isAccelKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("symphony:focus-search"));
      }
      if (!isEditingText && isAccelKey && e.key.toLowerCase() === "n") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("symphony:new-file"));
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleCopy, handleCut, handlePaste, handleDuplicate]);

  // Native OS file drop: when the host (Win32 IDropTarget / future macOS
  // dragging destination) catches an external drop, preload.js
  // dispatches a ``symphony:native-drop`` CustomEvent with screen-pixel
  // coordinates. Translate to client coords, resolve the nearest drop zone
  // by ``data-drop-folder``, and copy via Api.copyPathsInto so large files
  // never round-trip through base64.
  useEffect(() => {
    const handleNativeDrop = async (event) => {
      const detail = event?.detail || {};
      const { paths, screenX = 0, screenY = 0 } = detail;
      console.log("[symphony-drag] App.handleNativeDrop", detail);
      if (!Array.isArray(paths) || paths.length === 0) return;

      const supported = paths.filter((p) =>
        isSupportedDropExtension(p.split(/[\\/]/).pop() || ""),
      );
      if (supported.length === 0) {
        console.log("[symphony-drag] native drop has no supported extensions");
        window.dispatchEvent(new CustomEvent("symphony:invalid-drop"));
        return;
      }

      const dpr = window.devicePixelRatio || 1;
      const clientX = screenX / dpr - window.screenX;
      const clientY = screenY / dpr - window.screenY;
      let destination = null;
      try {
        const elements = document.elementsFromPoint(clientX, clientY) || [];
        for (const el of elements) {
          const folder = el?.closest?.("[data-drop-folder]");
          const value = folder?.getAttribute?.("data-drop-folder");
          if (value) {
            destination = value;
            break;
          }
        }
      } catch (err) {
        console.warn(
          "[symphony-drag] native-drop elementsFromPoint failed:",
          err,
        );
      }
      if (!destination && globalDirectory) {
        destination = globalDirectory;
      }
      console.log("[symphony-drag] resolved destination", {
        destination,
        clientX,
        clientY,
        dpr,
      });
      if (!destination) {
        window.dispatchEvent(new CustomEvent("symphony:invalid-drop"));
        return;
      }

      try {
        const activeDragPath =
          draggingFilePath || window.__symphonyDraggingFilePath;
        const normalizedDraggingPath = activeDragPath?.replace(/\\/g, "/");
        const inAppDragPath = supported.find(
          (sourcePath) =>
            sourcePath.replace(/\\/g, "/") === normalizedDraggingPath,
        );

        if (inAppDragPath) {
          const result = await moveInAppFileToDirectory(
            inAppDragPath,
            destination,
          );
          console.log("[symphony-drag] native in-app move result", result);
          setDraggingFilePath(null);
          window.__symphonyDraggingFilePath = null;
        } else {
          const result = await window.electronAPI.copyPathsInto(
            supported,
            destination,
          );
          console.log("[symphony-drag] copyPathsInto result", result);
        }
        setGlobalUpdateTimestamp(Date.now());
      } catch (err) {
        console.error("[symphony-drag] native drop failed:", err);
      }
    };
    window.addEventListener("symphony:native-drop", handleNativeDrop);
    return () =>
      window.removeEventListener("symphony:native-drop", handleNativeDrop);
  }, [
    draggingFilePath,
    globalDirectory,
    setDraggingFilePath,
    setGlobalUpdateTimestamp,
  ]);

  // Attach operator functions to window for Toolbar access
  window.symphonyOps = {
    handleCopy,
    handleCut,
    handlePaste,
    handleDuplicate,
  };

  return (
    <>
      <HomePage />
      <PendingFileHandoff />
    </>
  );
}

export default App;
