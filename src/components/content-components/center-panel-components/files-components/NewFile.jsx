import React, { useState } from "react";
import { Plus } from "lucide-react";
import path from "path-browserify";

import "./new-file.css";
import { useDirectory } from "@/contexts/DirectoryContext";
import fileIconAdd from "@/assets/file-icon-add.svg";

import GenericModal from "@/modals/GenericModal";
import NewFileModal from "@/modals/NewFileModal";

function NewFile() {
  const {
    globalDirectory,
    setGlobalDirectory,
    setGlobalUpdateTimestamp,
    viewType,
  } = useDirectory();
  const [showNewFile, setShowNewFile] = useState(false);

  const instantiateFile = async (title) => {
    console.log(title);
    document.body.style.cursor = "wait";
    const result = await window.electronAPI.doProcessCommand(
      path.join(globalDirectory, `${title}`),
      "instantiate"
    );
    document.body.style.cursor = "default";
    console.log(result);
    setShowNewFile(false);
    setGlobalUpdateTimestamp(Date.now());
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
          " new"
        }
        onClick={() => setShowNewFile(true)}
      >
        <img
          src={fileIconAdd}
          alt="File icon"
          color="#606060"
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
      <GenericModal isOpen={showNewFile} onClose={() => setShowNewFile(false)}>
        <NewFileModal onClose={instantiateFile} />
      </GenericModal>
    </>
  );
}

export default NewFile;
