import React, { useEffect, useState, useRef } from "react";
import { Info, LoaderCircle } from "lucide-react";

function ShowInfoModal({ filePath }) {
  const [fileInfo, setFileInfo] = useState(null);
  const [error, setError] = useState(null);
  const hasFetched = useRef(false); // <-- Track if fetch has already run

  const formatLabel = (input) => {
    const text = String(input ?? "N/A");
    if (!text) return "N/A";
    return text.charAt(0).toUpperCase() + text.slice(1);
  };

  const formatValue = (value) => {
    if (value === null || value === undefined) return "N/A";

    if (Array.isArray(value)) {
      return value.map((item) => String(item ?? "")).join(", ");
    }

    if (typeof value === "object") {
      return JSON.stringify(value);
    }

    const text = String(value);
    if (!text) return "N/A";
    return text.charAt(0).toUpperCase() + text.slice(1);
  };

  useEffect(() => {
    if (hasFetched.current || !filePath) return;

    hasFetched.current = true; // prevent future runs

    const fetchInfo = async () => {
      try {
        const result = await window.electronAPI.doProcessCommand(
          filePath,
          "retrieve"
        );

        if (result?.payload?.fileInfo) {
          setFileInfo(result.payload.fileInfo);
        } else {
          setError(result?.error || "Unknown error retrieving file info");
        }
      } catch (err) {
        setError(err.message || "Failed to retrieve info");
      }
    };

    fetchInfo();
  }, [filePath]);

  return (
    <>
      <div
        className="modal-title"
        style={{ display: "flex", marginBottom: "15px", alignItems: "center" }}
      >
        File Properties
      </div>

      {error && (
        <div className="modal-paragraph text-red-500">Error: {error}</div>
      )}

      {!fileInfo && !error && (
        <div
          className="modal-paragraph text-gray-500"
          style={{
            display: "flex",
            flexDirection: "row",
            gap: "10px",
            alignItems: "center",
            marginBottom: "5px",
          }}
        >
          <LoaderCircle className="spin" />
          Loading file info...
        </div>
      )}

      {fileInfo && (
        <div
          className="modal-paragraph space-y-2"
          style={{ marginBottom: "10px" }}
        >
          {Object.entries(fileInfo).map(([key, value]) => (
            <div key={key}>
              <strong style={{ marginRight: "4px" }}>
                {formatLabel(key)}:
              </strong>{" "}
              {formatValue(value)}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default ShowInfoModal;
