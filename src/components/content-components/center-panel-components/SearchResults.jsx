import React, { useState, useEffect, useContext } from "react";
import path from "path-browserify"; // Required for path operations in browser
import {
  Music,
  ChartNoAxesGantt,
  FolderClosed,
  X,
  KeyboardMusic,
  Star,
} from "lucide-react";

import Field from "../../../ui/Field";
import Tooltip from "@/ui/Tooltip";
import "./search-results.css";

import FileNotExist from "@/modals/FileNotExist";
import GenericModal from "@/modals/GenericModal";
import symphonyFileTypeIcon from "@/assets/symphony-file-type-icon.svg";

import { useDirectory } from "@/contexts/DirectoryContext";

function SearchResults({
  getSearchResults,
  getSearchTerm,
  getFocused,
  onClose,
}) {
  const [stars, setStars] = useState([]);
  const [showFileNotExist, setShowFileNotExist] = useState(false);
  const {
    setGlobalDirectory,
    globalUpdateTimestamp,
    setGlobalUpdateTimestamp,
    setSelectedFile,
  } = useDirectory();

  useEffect(() => {
    window.electronAPI.getStars().then((result) => {
      setStars(result);
    });
  }, [globalUpdateTimestamp]);

  const handleClick = (filePath) => {
    //console.log(filePath)
    const dirname = path.dirname(filePath);
    const uniPath = path.normalize(filePath).replace(/\\/g, "/");
    setGlobalDirectory(path.normalize(dirname).replace(/\\/g, "/"));
    setSelectedFile(path.basename(uniPath));
    console.log(path.basename(uniPath));
    //console.log(dirname);
  };

  const handleDoubleClick = async (filePath) => {
    const basename = path.basename(filePath);
    const dirname = path.dirname(filePath);
    const ext = path.extname(filePath);
    // console.log(ext);
    if (ext === ".symphony") {
      try {
        setGlobalUpdateTimestamp(Date.now());
        const result = await window.electronAPI.doProcessCommand(
          path.join(filePath.slice(0, -9)),
          "open",
          {},
        );
        console.log("Python script succeeded:", result.output);
      } catch (err) {
        console.error("Python script failed:", err.error || err);
        setShowFileNotExist(true);
        starsDelete(filePath);
      }
    } else {
      try {
        setGlobalUpdateTimestamp(Date.now());
        const response = await window.electronAPI.openNativeApp(filePath);
        if (!response.success) {
          //console.error(response.error);
          setShowFileNotExist(true);
          starsDelete(filePath);
        }
      } catch (err) {
        console.error(err);
        setShowFileNotExist(true);
        starsDelete(filePath);
      }
    }
    setSelectedFile(null);
  };

  const starsDelete = (filePath) => {
    window.electronAPI.removeStar(filePath);
    setGlobalUpdateTimestamp(Date.now());
  };

  return (
    <>
      <div className={"search-box" + (getFocused() ? " focused" : "")}>
        <div className="starred-label">
          STARRED
          {/* <button onClick={onClose} style={{ display: "flex" }}>
            <X size={15} />
          </button> */}
        </div>
        <div className="stars scrollable">
          {stars.length > 0 ? (
            stars.map((filePath, index) => {
              const normalizedPath = filePath.replace(/\\/g, "/");
              const basename = path.basename(normalizedPath);
              return (
                <Tooltip key={index} text={"..." + filePath.slice(-50)}>
                  <button
                    className="chip"
                    onClick={() => handleClick(normalizedPath)}
                    onDoubleClick={() => handleDoubleClick(normalizedPath)}
                  >
                    <Star size={12} fill="var(--foreground)" />
                    <span className="chip-name">{basename}</span>
                  </button>
                </Tooltip>
              );
            })
          ) : (
            <div
              style={{ marginBottom: "3px", color: "var(--muted-foreground)" }}
            >
              No Starred Files
            </div>
          )}
        </div>
        {getSearchTerm() !== "" && (
          <>
            <div className="results-label">Results for '{getSearchTerm()}'</div>
          </>
        )}
        {getSearchResults().length > 0 && (
          <>
            <div className="results">
              {getSearchResults().length > 0 ? (
                Object.entries(getSearchResults()).map((data, index) => {
                  const filePath = data[1].fullPath;
                  const normalizedPath = filePath.replace(/\\/g, "/");
                  const dirname = path.dirname(normalizedPath);
                  const ext = path.extname(normalizedPath).slice(1);
                  const fileTypes = {
                    mp3: Music,
                    wav: Music,
                    mid: KeyboardMusic,
                    "": FolderClosed,
                  };
                  const Icon = fileTypes[ext];
                  return (
                    <button
                      key={index}
                      className="search-result"
                      onClick={() => handleClick(normalizedPath)}
                      onDoubleClick={() => handleDoubleClick(normalizedPath)}
                    >
                      {ext === "symphony" ? (
                        <img
                          src={symphonyFileTypeIcon}
                          style={{
                            width: "14px",
                            height: "14px",
                            flexShrink: 0,
                          }}
                        />
                      ) : (
                        Icon && (
                          <Icon
                            size={14}
                            style={{
                              color: `var(--${
                                ext === ""
                                  ? null
                                  : ext === "wav" || ext === "mp3"
                                    ? "secondary"
                                    : "gray-50"
                              })`,
                            }}
                          />
                        )
                      )}
                      <span className="chip-name">
                        <span
                          style={{
                            fontWeight: "400",
                            color: "var(--muted-foreground)",
                          }}
                        >
                          {"..." + dirname.slice(-30) + "/"}
                        </span>
                        <span style={{ fontWeight: "700" }}>{data[1].el}</span>
                      </span>
                    </button>
                  );
                })
              ) : (
                <>No Starred Files.</>
              )}
            </div>
          </>
        )}
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
        />
      </GenericModal>
    </>
  );
}

export default SearchResults;
