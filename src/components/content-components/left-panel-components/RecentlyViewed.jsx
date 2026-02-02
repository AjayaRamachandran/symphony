import React, { useState, useEffect } from "react";

import {
  Music,
  ChartNoAxesGantt,
  FolderClosed,
  KeyboardMusic,
} from "lucide-react";
import path from "path-browserify";

import Tooltip from "@/components/Tooltip";
import "./recently-viewed.css";
import { useDirectory } from "@/contexts/DirectoryContext";
import FileNotExist from "@/modals/FileNotExist";
import GenericModal from "@/modals/GenericModal";

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
    symphony: ChartNoAxesGantt,
    mp3: Music,
    wav: Music,
    mid: KeyboardMusic,
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
          path.join(item.fileLocation, item.name)
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

  return (
    <>
      <div className="recently-viewed scrollable med-bg">
        {recentlyViewed.length > 0 &&
          recentlyViewed.map((item, recentIndex) => {
            if (recentIndex < 12) {
              const Icon = fileTypes[item.type];
              return (
                <button
                  className="recently-viewed-medium tooltip"
                  key={recentIndex}
                  onClick={() => handleClick(item)}
                  onDoubleClick={async () => {
                    await handleDoubleClick(item);
                  }}
                >
                  {Icon && (
                    <Icon
                      style={{ flexShrink: 0 }}
                      size={16}
                      strokeWidth={1.5}
                      color-type={
                        item.type === "mp3" || item.type === "wav"
                          ? "accent-color"
                          : item.type === "symphony"
                            ? "accent-color-2"
                            : "icon-color"
                      }
                    />
                  )}
                  <div className="truncated-text" style={{ marginLeft: "6px" }}>
                    {item.name}
                  </div>
                  <Tooltip text={item.name} />
                </button>
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
