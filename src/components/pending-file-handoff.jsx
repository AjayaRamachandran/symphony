import React, { useCallback, useEffect, useRef, useState } from "react";
import path from "path-browserify";

import GenericModal from "@/modals/generic-modal";
import FileNotExist from "@/modals/file-not-exist";
import GUIAlreadyRunning from "@/modals/gui-already-running";
import ImportExternalFile from "@/modals/import-external-file";
import { useDirectory } from "@/contexts/directory-context";

// Drives the OS-level "Open With Symphony" flow at both startup and on
// duplicate-launch (single-instance handoff). On each invocation we ask the
// backend whether a .symphony file is queued; if so, branch on whether the
// file's folder is registered with the Project Manager.
function PendingFileHandoff() {
  const runningRef = useRef(false);
  const [importTarget, setImportTarget] = useState(null);
  const [missingFile, setMissingFile] = useState(null);
  const [guiAlreadyRunning, setGuiAlreadyRunning] = useState(false);
  const { setGlobalDirectory, setGlobalUpdateTimestamp, setSelectedFile } =
    useDirectory();

  const runHandoff = useCallback(async () => {
    if (runningRef.current) return;
    runningRef.current = true;
    try {
      let pending = null;
      try {
        pending = await window.electronAPI.getPendingOpenFile();
      } catch (err) {
        console.warn("[symphony-open] getPendingOpenFile failed:", err);
        return;
      }
      if (!pending || !pending.path) return;

      if (!pending.exists) {
        setMissingFile(path.basename(pending.path.replace(/\\/g, "/")));
        return;
      }

      if (pending.knownLocation && pending.knownLocation.dir) {
        const dir = pending.knownLocation.dir;
        setGlobalDirectory(dir);
        setSelectedFile(path.basename(pending.path.replace(/\\/g, "/")));
        setGlobalUpdateTimestamp(Date.now());
        try {
          await window.electronAPI.runEditorProgram();
          const result = await window.electronAPI.doProcessCommand(
            pending.path,
            "open",
            {},
          );
          if (
            result &&
            result.status === "error" &&
            result.message === "GuiAlreadyRunningError"
          ) {
            setGuiAlreadyRunning(true);
          }
        } catch (err) {
          console.error("[symphony-open] doProcessCommand failed:", err);
        }
        return;
      }

      setImportTarget(pending.path);
    } finally {
      runningRef.current = false;
    }
  }, [setGlobalDirectory, setGlobalUpdateTimestamp, setSelectedFile]);

  useEffect(() => {
    runHandoff();
  }, [runHandoff]);

  // Re-run when the Rust launcher relays a duplicate-launch attempt through
  // the PM handoff server. The backend has already focused the window and
  // queued the new path (if any) into _PENDING_OPEN_FILE, so a fresh call to
  // getPendingOpenFile picks it up.
  useEffect(() => {
    const handler = () => {
      runHandoff();
    };
    window.addEventListener("symphony:second-instance", handler);
    return () =>
      window.removeEventListener("symphony:second-instance", handler);
  }, [runHandoff]);

  return (
    <>
      <GenericModal
        isOpen={Boolean(importTarget)}
        onClose={() => setImportTarget(null)}
      >
        {importTarget ? (
          <ImportExternalFile
            sourcePath={importTarget}
            onCancel={() => setImportTarget(null)}
            onImported={() => setImportTarget(null)}
          />
        ) : null}
      </GenericModal>
      <GenericModal
        isOpen={Boolean(missingFile)}
        onClose={() => setMissingFile(null)}
        showXButton={false}
      >
        <FileNotExist
          onComplete={() => setMissingFile(null)}
          fileName={() => missingFile || ""}
        />
      </GenericModal>
      <GenericModal
        isOpen={guiAlreadyRunning}
        onClose={() => setGuiAlreadyRunning(false)}
      >
        <GUIAlreadyRunning onComplete={() => setGuiAlreadyRunning(false)} />
      </GenericModal>
    </>
  );
}

export default PendingFileHandoff;
