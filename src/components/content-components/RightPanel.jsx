import React, { useState, useEffect, useRef } from "react";

import { PencilRuler } from "lucide-react";
import path from "path-browserify";

import Field from "../../ui/Field";
import Tooltip from "@/ui/Tooltip";

import "./right-panel.css";
import { useDirectory } from "@/contexts/DirectoryContext";

function RightPanel() {
  const [hovered, setHovered] = useState(false);
  const [fileName, setFileName] = useState("");
  const [metadata, setMetadata] = useState({});
  const [isMetadataLoading, setIsMetadataLoading] = useState(false);
  const [activeMetadataPath, setActiveMetadataPath] = useState("");
  const metadataDirtyRef = useRef(false);
  const metadataRef = useRef({});
  const metadataCommitTimeoutRef = useRef(null);
  const activeMetadataPathRef = useRef("");
  const [userFirstName, setUserFirstName] = useState("");
  const {
    selectedFile,
    setSelectedFile,
    setGlobalUpdateTimestamp,
    globalDirectory,
    setGlobalDirectory,
    tempFileName,
    setTempFileName,
  } = useDirectory();

  useEffect(() => {
    window.electronAPI.getUserSettings().then((result) => {
      setUserFirstName(result["user_name"] || null);
      // console.log(result["user_name"]);
    });
  }, [selectedFile]);

  const normalizeMetadata = (meta) => {
    if (!meta || typeof meta !== "object" || Array.isArray(meta) || meta.error) {
      return {};
    }
    return meta;
  };

  const metadataFromRetrieveResult = (result) => {
    const fileInfo = result?.payload?.fileInfo || {};
    return normalizeMetadata({
      Description: fileInfo["Description"] || "",
      Composer: fileInfo["Composer"] || "",
      Collaborators: fileInfo["Collaborators"] || "",
    });
  };

  const toProcessCommandMetadata = (meta) => ({
    description: meta?.Description || "",
    composer: meta?.Composer || "",
    collaborators: meta?.Collaborators || "",
  });

  // Load metadata when file changes
  useEffect(() => {
    setFileName(selectedFile ? selectedFile.slice(0, -9) : "");
    setTempFileName(selectedFile ? selectedFile.slice(0, -9) : "");
    const isSymphony = selectedFile && selectedFile.slice(-9) === ".symphony";
    setMetadata({});

    if (selectedFile && globalDirectory) {
      const filePath = path.join(globalDirectory, selectedFile);
      setActiveMetadataPath(filePath);
      activeMetadataPathRef.current = filePath;
      metadataDirtyRef.current = false;
      setIsMetadataLoading(true);

      let isStale = false;
      if (isSymphony) {
        window.electronAPI.doProcessCommand(filePath, "retrieve")
          .then((result) => {
            if (isStale) return;
            const normalized = metadataFromRetrieveResult(result);
            metadataRef.current = normalized;
            setMetadata(normalized);
          })
          .catch(() => {
            if (isStale) return;
            metadataRef.current = {};
            setMetadata({});
          })
          .finally(() => {
            if (isStale) return;
            setIsMetadataLoading(false);
          });

        return () => {
          isStale = true;
        };
      } else {
        setActiveMetadataPath("");
        activeMetadataPathRef.current = "";
        metadataDirtyRef.current = false;
        metadataRef.current = {};
        setMetadata({});
        setIsMetadataLoading(false);
      }
    }
  }, [selectedFile, globalDirectory]);

  const commitMetadataNow = async () => {
    const filePath = activeMetadataPathRef.current;
    if (!filePath || !metadataDirtyRef.current) return;

    const payload = toProcessCommandMetadata(metadataRef.current);
    metadataDirtyRef.current = false;
    try {
      await window.electronAPI.doProcessCommand(
        filePath,
        "update_metadata",
        { metadata: payload },
      );
    } catch (err) {
      // Keep unsaved state if command fails so future edits can retry.
      metadataDirtyRef.current = true;
      console.error("RightPanel::commitMetadataNow failed:", err);
    }
  };

  const scheduleMetadataCommit = () => {
    if (metadataCommitTimeoutRef.current) {
      clearTimeout(metadataCommitTimeoutRef.current);
    }
    metadataCommitTimeoutRef.current = setTimeout(() => {
      metadataCommitTimeoutRef.current = null;
      commitMetadataNow();
    }, 450);
  };

  useEffect(() => {
    return () => {
      if (metadataCommitTimeoutRef.current) {
        clearTimeout(metadataCommitTimeoutRef.current);
        metadataCommitTimeoutRef.current = null;
      }
      // Flush in-progress metadata edits before switching files/unmounting.
      commitMetadataNow();
    };
  }, [activeMetadataPath, globalDirectory, selectedFile]);

  const runProcessCommand = async (title) => {
    console.log(title);
    const result = await window.electronAPI.doProcessCommand(
      path.join(globalDirectory, `${title}`),
      "open",
      {},
    );
    console.log(result);
  };

  const updateTitle = (newName) => {
    console.log(selectedFile);
    console.log(globalDirectory);
    console.log(newName);

    window.electronAPI.renameFile(path.join(globalDirectory, selectedFile), newName)
      .then((result) => {
        if (result.success) {
          setSelectedFile(newName + ".symphony");
          setGlobalUpdateTimestamp(Date.now());
          console.log(`RightPanel.jsx::updateTitle() - newName: ${newName}`);
        } else {
          setSelectedFile(newName + ".symphony");
          setGlobalUpdateTimestamp(Date.now());
          console.error(result.error);
        }
      });
  };

  // Update draft metadata while typing.
  const updateMetadataField = (field, value) => {
    const nextMetadata = {
      ...normalizeMetadata(metadataRef.current),
      [field]: value,
    };
    metadataRef.current = nextMetadata;
    setMetadata(nextMetadata);
    metadataDirtyRef.current = true;
    scheduleMetadataCommit();
  };

  // Commit metadata explicitly on blur / Enter.
  const commitMetadata = () => {
    if (metadataCommitTimeoutRef.current) {
      clearTimeout(metadataCommitTimeoutRef.current);
      metadataCommitTimeoutRef.current = null;
    }
    commitMetadataNow();
  };

  // Only update tempFileName on change, and update actual file on blur
  const handleTitleChange = (e) => {
    setTempFileName(e.target.value);
  };
  const handleTitleBlur = (e) => {
    if (tempFileName !== fileName) {
      updateTitle(tempFileName || "Untitled " + Date.now().toString());
    }
  };

  return (
    <div className="content-panel-container right">
      <>
        <div>
          <div className="med-title" >
            Details
          </div>
          {selectedFile && selectedFile.slice(-9) === ".symphony" ? (
            <>
              <div className="field-label">Title</div>
              <Field
                value={tempFileName}
                style={{ height: "33px" }}
                onChange={handleTitleChange}
                onBlur={handleTitleBlur}
                singleLine={true}
              />

              <div className="field-label">Description</div>
              <div
                className={`metadata-field-crossfade ${isMetadataLoading ? "loading" : "loaded"}`}
              >
                <Field
                  value={metadata.Description || ""}
                  style={{ height: "120px", fontSize: "1.2em" }}
                  onChange={(e) =>
                    updateMetadataField("Description", e.target.value)
                  }
                  onBlur={commitMetadata}
                />
                <div className="metadata-field-skeleton-layer" aria-hidden="true">
                  <div className="field-skeleton large" />
                </div>
              </div>

              <div className="field-label">Composer / Arr.</div>
              <div
                className={`metadata-field-crossfade ${isMetadataLoading ? "loading" : "loaded"}`}
              >
                <Field
                  placeholder={userFirstName}
                  value={metadata.Composer}
                  style={{ height: "70px", fontSize: "1.2em" }}
                  onChange={(e) =>
                    updateMetadataField("Composer", e.target.value)
                  }
                  onBlur={commitMetadata}
                />
                <div className="metadata-field-skeleton-layer" aria-hidden="true">
                  <div className="field-skeleton small" />
                </div>
              </div>

              <div className="field-label">Collaborators</div>
              <div
                className={`metadata-field-crossfade ${isMetadataLoading ? "loading" : "loaded"}`}
              >
                <Field
                  value={metadata.Collaborators || ""}
                  style={{ height: "70px", fontSize: "1.2em" }}
                  onChange={(e) =>
                    updateMetadataField("Collaborators", e.target.value)
                  }
                  onBlur={commitMetadata}
                />
                <div className="metadata-field-skeleton-layer" aria-hidden="true">
                  <div className="field-skeleton medium" />
                </div>
              </div>

              <div className="field-label">File Location</div>
              <Tooltip
                text={
                  globalDirectory && path.join(globalDirectory, selectedFile)
                }
                className="tooltip-block"
              >
                <div
                  className="field scrollable dark-bg"
                  style={{
                    whiteSpace: "nowrap",
                    textOverflow: "ellipsis",
                    padding: "7px 7px 7px 7px",
                    fontSize: "13px",
                    cursor: "pointer",
                    fontStyle: "italic",
                  }}
                >
                  {path.join(globalDirectory, selectedFile)}
                </div>
              </Tooltip>
            </>
          ) : (
            <>
              <div className="faded">
                Select a Symphony to view its details.
              </div>
            </>
          )}
        </div>

        <Tooltip
          text={
            selectedFile && selectedFile.slice(-9) === ".symphony"
              ? "Open the selected Symphony in the Editor."
              : "Select a Symphony to open it in the Editor."
          }
          className="tooltip-block"
        >
          <button
            className={
              "call-to-action" +
              (selectedFile && selectedFile.slice(-9) === ".symphony"
                ? ""
                : " inactive")
            }

            style={{ transition: "filter 0.2s, border 0.4s, background 0.4s" }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            onClick={
              selectedFile && selectedFile.slice(-9) === ".symphony"
                ? () => runProcessCommand(selectedFile)
                : undefined
            }
          >
            <div>Open in Editor</div>
            <PencilRuler size={16} strokeWidth={2.5} />
          </button>
        </Tooltip>
      </>
    </div>
  );
}

export default RightPanel;
