import React, { useEffect, useState } from "react";
import path from "path-browserify";
import { FolderClosed, FolderPlus } from "lucide-react";

import Dropdown from "@/ui/dropdown";
import GenericModal from "@/modals/generic-modal";
import NewFolder from "@/modals/new-folder";
import { useDirectory } from "@/contexts/directory-context";

// Modal shown when the user opens a .symphony file via Explorer / Open With
// whose containing folder isn't registered with the Project Manager. Lets
// them pick (or add) a Projects-section folder, copies the file in, and then
// boots the editor on the resulting path.
function ImportExternalFile({ sourcePath, onCancel, onImported }) {
  const [projectFolders, setProjectFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const { setGlobalDirectory, setGlobalUpdateTimestamp, setSelectedFile } =
    useDirectory();

  const fileName = sourcePath
    ? path.basename(sourcePath.replace(/\\/g, "/"))
    : "this file";

  const loadFolders = async () => {
    const directory = await window.electronAPI.getDirectory();
    const projects = Array.isArray(directory?.Projects) ? directory.Projects : [];
    const entries = projects
      .map((entry) => {
        if (!entry || typeof entry !== "object") return null;
        const [alias, dirPath] = Object.entries(entry)[0] || [];
        if (!alias || !dirPath) return null;
        return { alias, dirPath };
      })
      .filter(Boolean);
    setProjectFolders(entries);
    return entries;
  };

  useEffect(() => {
    loadFolders().then((entries) => {
      if (entries.length > 0) {
        setSelectedFolder({
          label: entries[0].alias,
          subLabel: entries[0].dirPath,
          dirPath: entries[0].dirPath,
          icon: FolderClosed,
        });
      }
    });
  }, []);

  const folderOptions = projectFolders.map((entry) => ({
    label: entry.alias,
    subLabel: entry.dirPath,
    dirPath: entry.dirPath,
    icon: FolderClosed,
  }));

  const addNewOption = {
    label: "Add new folder...",
    icon: FolderPlus,
    isAddNew: true,
  };

  const dropdownOptions = [...folderOptions, addNewOption];

  const handleSelect = (option) => {
    if (option?.isAddNew) {
      setShowNewFolder(true);
      return;
    }
    setSelectedFolder(option);
  };

  const importAndOpen = async () => {
    if (!selectedFolder?.dirPath) return;
    setBusy(true);
    setError(null);
    try {
      const copyResult = await window.electronAPI.copyAndOpenSymphonyFile(
        sourcePath,
        selectedFolder.dirPath,
      );
      if (!copyResult?.success) {
        setError(copyResult?.error || "Could not copy the file.");
        setBusy(false);
        return;
      }
      const newPath = copyResult.path;
      // Surface the destination folder in the project manager so the imported
      // file is visible immediately when the editor closes back to PM.
      setGlobalDirectory(selectedFolder.dirPath);
      setSelectedFile(path.basename(newPath.replace(/\\/g, "/")));
      setGlobalUpdateTimestamp(Date.now());

      await window.electronAPI.runEditorProgram();
      await window.electronAPI.doProcessCommand(newPath, "open", {});
      onImported?.();
    } catch (exc) {
      console.error("importAndOpen failed:", exc);
      setError(String(exc?.message || exc));
      setBusy(false);
    }
  };

  return (
    <>
      <div className="modal-title" style={{ marginBottom: "15px" }}>
        Import a Symphony
      </div>
      <div className="modal-paragraph" style={{ marginBottom: "20px" }}>
        "{fileName}" isn't in your Symphony directory.
        Pick a project folder to copy it into.
      </div>
      <div className="modal-body">Destination folder</div>
      <Dropdown
        options={dropdownOptions}
        onSelect={handleSelect}
        value={selectedFolder}
        placeholder={
          projectFolders.length === 0
            ? "No folders yet — add one"
            : "Choose a folder"
        }
      />
      {error ? (
        <div
          className="modal-paragraph"
          style={{
            color: "var(--destructive, #c44)",
            marginTop: "12px",
            fontSize: "13px",
          }}
        >
          {error}
        </div>
      ) : null}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "8px",
          marginTop: "24px",
        }}
      >
        <button
          className={
            !selectedFolder?.dirPath || busy
              ? "call-to-action-2 locked"
              : "call-to-action-2"
          }
          onClick={
            !selectedFolder?.dirPath || busy ? undefined : importAndOpen
          }
        >
          {busy ? "Importing..." : "Import & Open"}
        </button>
      </div>
      <GenericModal
        isOpen={showNewFolder}
        onClose={() => setShowNewFolder(false)}
      >
        <NewFolder
          defaultDestProp="Projects"
          onClose={async () => {
            setShowNewFolder(false);
            const entries = await loadFolders();
            const latest = entries[entries.length - 1];
            if (latest) {
              setSelectedFolder({
                label: latest.alias,
                subLabel: latest.dirPath,
                dirPath: latest.dirPath,
                icon: FolderClosed,
              });
            }
          }}
          onConflict={() => setShowNewFolder(false)}
        />
      </GenericModal>
    </>
  );
}

export default ImportExternalFile;
