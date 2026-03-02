import React, { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import path from "path-browserify";

import { useDirectory } from "@/contexts/DirectoryContext";
import fileIconAdd from "@/assets/file-icon-add.svg";
import Tooltip from "@/ui/Tooltip";

import GenericModal from "@/modals/GenericModal";
import NewFileModal from "@/modals/NewFileModal";

function NewFile() {
  const {
    globalDirectory,
    setGlobalDirectory,
    setSelectedFile,
    setGlobalUpdateTimestamp,
    viewType,
  } = useDirectory();
  const [showNewFile, setShowNewFile] = useState(false);

  useEffect(() => {
    const handleOpenNewFile = () => {
      setShowNewFile(true);
    };

    window.addEventListener("symphony:new-file", handleOpenNewFile);
    return () => {
      window.removeEventListener("symphony:new-file", handleOpenNewFile);
    };
  }, []);

  const instantiateFile = async (title) => {
    console.log(title);
    document.body.style.cursor = "wait";
    const result = await window.electronAPI.doProcessCommand(
      path.join(globalDirectory, `${title}`),
      "instantiate",
      {},
    );
    document.body.style.cursor = "default";
    console.log(result);
    setShowNewFile(false);
    setGlobalUpdateTimestamp(Date.now());
    if (result.status === "success") {
      setSelectedFile(path.basename(result.payload.project_file_path));
      await window.electronAPI.doProcessCommand(
        result.payload.project_file_path,
        "open",
        {},
      );
    }
  };

  return (
    <>
      <Tooltip text="Create New" altText={navigator.platform && navigator.platform.startsWith("Mac") ? "⌘ + N" : "Ctrl + N"}>
        <button
          id="new-file-button"
          className={
            "file-select-box" +
            (viewType === "grid"
              ? ""
              : viewType === "content"
                ? "-content"
                : "-list") +
            " new"
          }
          onClick={() => setShowNewFile(true)}
        >
          <img
            src={fileIconAdd}
            alt="File icon"
            color="var(--gray-50)"
            height={viewType === "grid" ? 78 : viewType === "content" ? 55 : 21}
            style={{ marginTop: viewType === "list" ? "3px" : "0" }}
          />
          <div
            style={{
              marginTop:
                viewType == "grid"
                  ? "0px"
                  : viewType == "content"
                    ? "15px"
                    : "3px",
            }}
          >
            New Symphony
          </div>
        </button>
      </Tooltip>
      <GenericModal isOpen={showNewFile} onClose={() => setShowNewFile(false)}>
        <NewFileModal onClose={instantiateFile} />
      </GenericModal>
    </>
  );
}

export default NewFile;
