import React from "react";
import { FolderOpen } from "lucide-react";

import Tooltip from "@/ui/Tooltip";

function SelectFile({
  selectedPath = "",
  onClick,
  placeholder = "Open File Explorer...",
  className = "modal-file-explorer-button",
}) {
  const label = selectedPath === "" ? placeholder : selectedPath;

  const button = (
    <button className={className} onClick={onClick}>
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
        {label}
      </span>
    </button>
  );

  if (selectedPath === "") {
    return button;
  }

  return <Tooltip text={`${selectedPath}  ⦁  Click to Change`}>{button}</Tooltip>;
}

export default SelectFile;
