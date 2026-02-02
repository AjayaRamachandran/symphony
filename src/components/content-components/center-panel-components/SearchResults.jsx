import React, { useState, useEffect, useContext } from "react";
import path from "path-browserify"; // Required for path operations in browser
import {
  Music,
  ChartNoAxesGantt,
  FolderClosed,
  X,
  KeyboardMusic,
} from "lucide-react";


import Field from "../right-panel-components/Field";
import Tooltip from "@/components/Tooltip";
import "./search-results.css";

import FileNotExist from "@/modals/FileNotExist";
import GenericModal from "@/modals/GenericModal";

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
        const result = await window.electronAPI.doProcessCommand([
          "open",
          basename,
          dirname,
        ]);
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
      {getFocused() && (
        <div className="search-box">
          <div className="starred-label">
            STARRED
            <button onClick={onClose}>
              <X size={15} />
            </button>
          </div>
          <div className="stars scrollable">
            {stars.length > 0 ? (
              stars.map((filePath, index) => {
                const normalizedPath = filePath.replace(/\\/g, "/");
                const basename = path.basename(normalizedPath);
                return (
                  <button
                    key={index}
                    className="chip tooltip"
                    onClick={() => handleClick(normalizedPath)}
                    onDoubleClick={() => handleDoubleClick(normalizedPath)}
                  >
                    <Tooltip text={"..." + filePath.slice(-50)} />
                    <i
                      className="bi bi-star-fill"
                      style={{
                        marginRight: "4px",
                        alignItems: "center",
                        fontSize: "10px",
                        marginBottom: "1px",
                        marginTop: "1px",
                      }}
                    ></i>
                    <span className="chip-name">{basename}</span>
                  </button>
                );
              })
            ) : (
              <>No Starred Files.</>
            )}
          </div>
          {getSearchTerm() !== "" && (
            <>
              <div className="results-label">
                Results for '{getSearchTerm()}'
              </div>
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
                      symphony: ChartNoAxesGantt,
                      mp3: Music,
                      wav: Music,
                      mid: KeyboardMusic,
                      "": FolderClosed,
                    };
                    const Icon = fileTypes[ext];
                    return (
                      <button
                        key={index}
                        className="search-result tooltip"
                        onClick={() => handleClick(normalizedPath)}
                        onDoubleClick={() => handleDoubleClick(normalizedPath)}
                      >
                        <Icon
                          size={14}
                          color-type={
                            ext === ""
                              ? null
                              : ext === "symphony"
                                ? "accent-color-2"
                                : ext === "wav" || ext === "mp3"
                                  ? "accent-color"
                                  : "icon-color"
                          }
                        />
                        <span className="chip-name">
                          <span style={{ fontWeight: "400", color: "var(--muted-foreground)" }}>
                            {"..." + dirname.slice(-30) + "/"}
                          </span>
                          <span style={{ fontWeight: "700" }}>
                            {data[1].el}
                          </span>
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
      )}
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
