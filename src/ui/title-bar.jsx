import React, { useState, useEffect } from "react";

import { Square, Copy, Minus, X } from "lucide-react";
import Icon from "@/assets/icon-dark.svg";
import ProgramData from "@/assets/program-data.json";

import "@/ui/title-bar.css";

function getWindowApi(api) {
  if (api) return api;
  if (typeof window === "undefined") return null;
  return window.electronAPI || window.editorAPI || null;
}

function TitleBar({
  title = `Project Manager - Symphony v${ProgramData.version}`,
  icon = Icon,
  api = null,
}) {
  const windowApi = getWindowApi(api);
  const [isMaximized, setIsMaximized] = useState(false);
  const [isFocused, setIsFocused] = useState(true);
  const [isMac, setIsMac] = useState(() => getWindowApi(api)?.platform === "darwin");

  useEffect(() => {
    if (!windowApi) return undefined;

    const off = windowApi.onWindowStateChange?.(setIsMaximized);
    if (windowApi.platform) {
      setIsMac(windowApi.platform === "darwin");
    } else if (windowApi.getPlatform) {
      windowApi.getPlatform().then((platform) => setIsMac(platform === "darwin")).catch(() => {});
    }

    return () => off?.();
  }, [windowApi]);

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
      <div className={`titlebar ${isMac ? "mac pywebview-drag-region" : ""}`}>
        {!isMac && <div className="titlebar-drag-zone pywebview-drag-region" />}

        {isMac && (
          <div
            className={`mac-controls ${!isFocused ? "unfocused" : ""}`}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="mac-buttons">
              <span
                className="mac-btn close"
                onClick={() => windowApi?.close?.()}
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
                onClick={() => windowApi?.minimize?.()}
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
                onClick={() => windowApi?.maximize?.()}
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
          {icon && <img src={icon} width="16px" style={{ filter: "drop-shadow(0 1px 2px rgba(0, 0, 0, 0.5))" }} />}
          <div>{title}</div>
        </div>

        {!isMac && (
          <div
            className="window-controls"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <button
              className="topbar-button"
              onClick={() => windowApi?.minimize?.()}
            >
              <Minus size={13} />
            </button>
            <button
              className="topbar-button"
              onClick={() => windowApi?.maximize?.()}
            >
              {isMaximized ? (
                <Copy size={12} style={{ transform: "rotate(90deg)" }} />
              ) : (
                <Square size={11} />
              )}
            </button>
            <button
              className="topbar-button x-button"
              onClick={() => windowApi?.close?.()}
            >
              <X size={15} strokeWidth={1.7} />
            </button>
          </div>
        )}
      </div>
    </>
  );
}

export default TitleBar;
