import React, { useState, useEffect } from "react";

import {
  Music,
  FolderClosed,
  KeyboardMusic,
  Music4,
  Trash2,
} from "lucide-react";
import path from "path-browserify";

import Tooltip from "@/ui/Tooltip";
import "./recently-viewed.css";
import { useDirectory } from "@/contexts/DirectoryContext";
import FileNotExist from "@/modals/FileNotExist";
import GenericModal from "@/modals/GenericModal";
import symphonyFileTypeIcon from "@/assets/symphony-file-type-icon.svg";

function RecentlyViewed() {
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const [showFileNotExist, setShowFileNotExist] = useState(false);
  const [launchItemName, setLaunchItemName] = useState(null);
  const {
    setGlobalDirectory,
    setSelectedFile,
    globalUpdateTimestamp,
    setGlobalUpdateTimestamp,
  } = useDirectory();
  const fileTypes = {
    mp3: Music,
    wav: Music,
    mid: KeyboardMusic,
    musicxml: Music4,
    "": FolderClosed,
  };

  const getItemName = () => {
    return launchItemName;
  };

  useEffect(() => {
    window.electronAPI
      .getRecentlyViewed()
      .then((items) => {
        setRecentlyViewed(Array.isArray(items) ? items : []);
      })
      .catch(() => setRecentlyViewed([]));
  }, [globalUpdateTimestamp]);

  // Handle single and double click
  const handleClick = (item) => {
    if (item.fileLocation && item.type === "symphony") {
      setGlobalDirectory(item.fileLocation.replace(/\\/g, "/"));
      setSelectedFile(item.name);
      console.log(item.fileLocation.replace(/\\/g, "/"));
      console.log(item.name);
    }
  };

  const handleDoubleClick = async (item) => {
    setLaunchItemName(item.name);
    if (item.type === "symphony") {
      try {
        setGlobalUpdateTimestamp(Date.now());
        const result = await window.electronAPI.doProcessCommand([
          "open",
          item.name,
          item.fileLocation,
        ]);
        console.log("Python script succeeded:", result.output);
      } catch (err) {
        console.error("Python script failed:", err.error || err);
        setShowFileNotExist(true);
        recentlyViewedDelete(item);
      }
    } else {
      try {
        setGlobalUpdateTimestamp(Date.now());
        const response = await window.electronAPI.openNativeApp(
          path.join(item.fileLocation, item.name),
        );
        if (!response.success) {
          //console.error(response.error);
          setShowFileNotExist(true);
          recentlyViewedDelete(item);
        }
      } catch (err) {
        console.error(err);
        setShowFileNotExist(true);
        recentlyViewedDelete(item);
      }
    }
    setSelectedFile(null);
  };

  const recentlyViewedDelete = (item) => {
    window.electronAPI.recentlyViewedDelete(item.name);
    setGlobalUpdateTimestamp(Date.now());
  };

  const clearRecentlyViewed = async () => {
    try {
      await window.electronAPI.clearRecentlyViewed();
      setRecentlyViewed([]);
      setGlobalUpdateTimestamp(Date.now());
    } catch (error) {
      console.error("Failed to clear recently viewed:", error);
    }
  };

  return (
    <>
      <div className="section-title-row">
        <div className="section-title uppercase">Recently Launched</div>
        <Tooltip text="Empty Recents">
          <button
            className="recently-viewed-clear-button"
            onClick={clearRecentlyViewed}
            disabled={recentlyViewed.length === 0}
          >
            <Trash2 size={14} strokeWidth={1.6} />
          </button>
        </Tooltip>
      </div>
      <div className="recently-viewed scrollable med-bg">
        {recentlyViewed.length > 0 &&
          recentlyViewed.map((item, recentIndex) => {
            if (recentIndex < 9) {
              const Icon = fileTypes[item.type];
              return (
                <Tooltip
                  key={recentIndex}
                  text={item.name}
                  className="tooltip-block"
                >
                  <button
                    className="recently-viewed-item"
                    onClick={() => handleClick(item)}
                    onDoubleClick={async () => {
                      await handleDoubleClick(item);
                    }}
                  >
                    {item.type === "symphony" ? (
                      <img
                        src={symphonyFileTypeIcon}
                        style={{ width: "16px", height: "16px", flexShrink: 0 }}
                      />
                    ) : (
                      Icon && (
                        <Icon
                          size={16}
                          strokeWidth={1.5}
                          style={{
                            flexShrink: 0,
                            color: `var(--${
                              ["wav", "flac", "mp3", "mid", "musicxml"].includes(item.type)
                                ? "secondary"
                                : "gray-50"
                            })`,
                          }}
                        />
                      )
                    )}
                    <div
                      className="truncated-text"
                      style={{ marginLeft: "6px" }}
                    >
                      {item.name}
                    </div>
                  </button>
                </Tooltip>
              );
            }
          })}
      </div>
      <GenericModal
        isOpen={showFileNotExist}
        onClose={() => {
          setShowFileNotExist(false);
        }}
        showXButton={false}
      >
        <FileNotExist
          onComplete={() => {
            setShowFileNotExist(false);
          }}
          fileName={getItemName}
        />
      </GenericModal>
    </>
  );
}

export default RecentlyViewed;
