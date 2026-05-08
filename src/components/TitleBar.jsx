import React, { useState, useEffect, useRef } from "react";

import { Square, Copy } from "lucide-react";
import * as Neutralino from "@neutralinojs/lib";
import Icon from "@/assets/icon-dark.svg";
import ProgramData from "@/assets/program-data.json";

import "./titlebar.css";

function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(false);
  const [isFocused, setIsFocused] = useState(true);
  const [isMac, setIsMac] = useState(true);
  const titlebarRef = useRef(null);
  const winControlsRef = useRef(null);
  const macControlsRef = useRef(null);

  useEffect(() => {
    window.electronAPI.onWindowStateChange(setIsMaximized);
    setIsMac(window.electronAPI.platform === "darwin");
  }, []);

  // Register the title bar as a draggable region. setDraggableRegion's
  // `exclusions` accept DOM IDs or HTMLElement refs (NOT CSS selectors),
  // so we pass the actual control wrappers — otherwise the drag handler
  // swallows clicks on min/max/close.
  useEffect(() => {
    let cancelled = false;
    let handle = null;
    (async () => {
      if (!titlebarRef.current) return;
      const exclusions = [winControlsRef.current, macControlsRef.current].filter(
        Boolean,
      );
      try {
        handle = await Neutralino.window.setDraggableRegion(titlebarRef.current, {
          exclusions,
        });
      } catch (err) {
        if (!cancelled) console.debug("setDraggableRegion skipped:", err);
      }
    })();
    return () => {
      cancelled = true;
      if (handle && titlebarRef.current) {
        Neutralino.window.unsetDraggableRegion(titlebarRef.current).catch(() => {});
      }
    };
  }, [isMac]);

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
      <div ref={titlebarRef} className={`titlebar ${isMac ? "mac" : ""}`}>
        {isMac && (
          <div
            ref={macControlsRef}
            className={`mac-controls ${!isFocused ? "unfocused" : ""}`}
          >
            <div className="mac-buttons">
              <span
                className="mac-btn close"
                onClick={() => window.electronAPI.close()}
              >
                <svg
                  className="mac-btn-icon"
                  viewBox="0 0 10 10"
                  aria-hidden="true"
                >
                  <path
                    d="M3 3 L7 7 M7 3 L3 7"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                  />
                </svg>
              </span>
              <span
                className="mac-btn minimize"
                onClick={() => window.electronAPI.minimize()}
              >
                <svg
                  className="mac-btn-icon"
                  viewBox="0 0 10 10"
                  aria-hidden="true"
                >
                  <path
                    d="M3 5 L7 5"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                  />
                </svg>
              </span>
              <span
                className="mac-btn maximize"
                onClick={() => window.electronAPI.maximize()}
              >
                <svg
                  className="mac-btn-icon"
                  viewBox="0 0 10 10"
                  aria-hidden="true"
                >
                  <path
                    d="M3 7 L3 4 L6 7 Z M7 3 L7 6 L4 3 Z"
                    fill="currentColor"
                  />
                </svg>
              </span>
            </div>
          </div>
        )}

        <div className="titlebar-center">
          <img src={Icon} width="16px" style={{ filter: "drop-shadow(0 1px 2px rgba(0, 0, 0, 0.5))" }} />
          <div>Project Manager - Symphony v{ProgramData.version}</div>
        </div>

        {!isMac && (
          <div ref={winControlsRef} className="window-controls">
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
