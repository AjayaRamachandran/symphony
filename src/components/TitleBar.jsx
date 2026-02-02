import React, { useState, useEffect } from "react";

import { Square, Copy } from "lucide-react";
import Icon from "@/assets/icon-dark.svg";

function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(false);
  const [isFocused, setIsFocused] = useState(true);

  useEffect(() => {
    // Listen for maximize/unmaximize from backend
    window.electronAPI.onWindowStateChange(setIsMaximized);
  }, []);

  const isMac = window.electronAPI.platform === "darwin";

  useEffect(() => {
    const onFocus = () => setIsFocused(true);
    const onBlur = () => setIsFocused(false);

    window.addEventListener("focus", onFocus);
    window.addEventListener("blur", onBlur);

    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("blur", onBlur);
    };
  }, []);

  return (
    <>
      <div className={`titlebar ${isMac ? "mac" : ""}`}>
        {isMac && (
          <div className={`mac-controls ${!isFocused ? "unfocused" : ""}`}>
            <div className="mac-buttons">
              <span
                className="mac-btn close"
                onClick={() => window.electronAPI.close()}
              />
              <span
                className="mac-btn minimize"
                onClick={() => window.electronAPI.minimize()}
              />
              <span
                className="mac-btn maximize"
                onClick={() => window.electronAPI.maximize()}
              />
            </div>
          </div>
        )}

        <div className="titlebar-center">
          <img src={Icon} width="16px" />
          <div>Project Manager - Symphony v1.0 Beta</div>
        </div>

        {!isMac && (
          <div className="window-controls">
            <button
              className="bi bi-dash-lg"
              topbar-buttons="true"
              onClick={() => window.electronAPI.minimize()}
            ></button>
            <button
              topbar-buttons="true"
              onClick={() => window.electronAPI.maximize()}
            >
              {isMaximized ? (
                <Copy size={12} style={{ transform: "rotate(90deg)" }} />
              ) : (
                <Square size={11} />
              )}
            </button>
            <button
              className="bi bi-x-lg x-button"
              topbar-buttons="true"
              onClick={() => window.electronAPI.close()}
            ></button>
          </div>
        )}
      </div>
    </>
  );
}

export default TitleBar;
