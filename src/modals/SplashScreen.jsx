import React, { useState, useEffect } from "react";
import {
  Music,
  ChartNoAxesGantt,
  FolderClosed,
  BookMarked,
  GitBranch,
  Play,
  KeyboardMusic,
} from "lucide-react";
import path from "path-browserify";


import Tooltip from "@/components/Tooltip";
import "@/components/content-components/left-panel-components/recently-viewed.css";
import GenericModal from "@/modals/GenericModal";
import FileNotExist from "@/modals/FileNotExist";

import banner from "@/assets/banner.svg";
import { useDirectory } from "@/contexts/DirectoryContext";

function SplashScreen({ onComplete }) {
  const [userName, setUserName] = useState("");
  const [page, setPage] = useState(0);
  const [userFirstName, setUserFirstName] = useState("");
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const [launchItemName, setLaunchItemName] = useState(null);
  const [showFileNotExist, setShowFileNotExist] = useState(false);
  const { globalUpdateTimestamp, setGlobalUpdateTimestamp, setSelectedFile } =
    useDirectory();

  const fileTypes = {
    symphony: ChartNoAxesGantt,
    mp3: Music,
    wav: Music,
    mid: KeyboardMusic,
    "": FolderClosed,
  };

  useEffect(() => {
    window.electronAPI.getUserSettings().then((result) => {
      setUserFirstName(result["user_name"] || null);
    });
  }, []);

  useEffect(() => {
    window.electronAPI
      .getRecentlyViewed()
      .then((items) => {
        setRecentlyViewed(Array.isArray(items) ? items : []);
      })
      .catch(() => setRecentlyViewed([]));
  }, [globalUpdateTimestamp]);

  const handleClick = async (item) => {
    setLaunchItemName(item.name);
    if (item.type === "symphony") {
      try {
        setGlobalUpdateTimestamp(Date.now());
        const result = await window.electronAPI.doProcessCommand(
          path.join(item.fileLocation, item.name),
          "open",
          {}
        );
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

  // open external link in default browser
  const openExternal = (url) => {
    window.electronAPI.openExternal(url);
  };

  return (
    <>
      <div className="banner">
        <img src={banner} style={{ width: "500px", display: "block" }}></img>
      </div>
      <div style={{ padding: "30px", borderTop: "1px solid var(--tinted-background)" }}>
        <div
          className="modal-big-title"
          text-style="display"
          style={{ margin: "0px 0px", fontSize: "28px" }}
        >
          {userFirstName ? "Hi " + userFirstName.split(" ")[0] : "Welcome"}!
        </div>
        <div
          className="modal-paragraph"
          text-style="display"
          style={{ fontSize: "14px", marginBottom: "28px", marginTop: "8px" }}
        >
          Let's create something amazing.
        </div>
        {recentlyViewed.length > 0 && (
          <>
            <div
              className="modal-body"
              text-style="display"
              style={{
                fontSize: "18px",
                marginBottom: "8px",
                marginTop: "15px",
              }}
            >
              Jump Back In
            </div>
            <div className="quick-launch scrollable med-bg">
              {recentlyViewed.map((item, recentIndex) => {
                if (recentIndex < 3) {
                  const Icon = fileTypes[item.type];
                  return (
                    <button
                      className="quick-launch-medium tooltip"
                      key={recentIndex}
                      onClick={() => handleClick(item)}
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
                      <div
                        className="truncated-text"
                        style={{ marginLeft: "6px" }}
                      >
                        {item.name}
                      </div>
                    </button>
                  );
                }
              })}
            </div>
          </>
        )}
        <div
          className="modal-body"
          text-style="display"
          style={{ fontSize: "18px", marginBottom: "8px", marginTop: "15px" }}
        >
          Resources
        </div>
        <div className="quick-launch scrollable med-bg">
          <button
            className="quick-launch-medium tooltip"
            onClick={() => openExternal("https://symphony.nimbial.com/docs")}
          >
            <BookMarked style={{ flexShrink: 0 }} size={16} strokeWidth={1.5} />
            <div className="truncated-text" style={{ marginLeft: "6px" }}>
              Learn how to use Symphony{" "}
              <span style={{ opacity: "0.5", fontStyle: "italic" }}>
                (recommended)
              </span>
            </div>
          </button>
          <button
            className="quick-launch-medium tooltip"
            onClick={() =>
              openExternal("https://symphony.nimbial.com/download")
            }
          >
            <GitBranch style={{ flexShrink: 0 }} size={16} strokeWidth={1.5} />
            <div className="truncated-text" style={{ marginLeft: "6px" }}>
              See the latest Release Notes
            </div>
          </button>
          <button
            className="quick-launch-medium tooltip"
            onClick={() => openExternal("https://symphony.nimbial.com")}
          >
            <Play style={{ flexShrink: 0 }} size={16} strokeWidth={1.5} />
            <div className="truncated-text" style={{ marginLeft: "6px" }}>
              Watch the launch video
            </div>
          </button>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            height: "min-content",
            alignItems: "flex-end",
          }}
        >
          <button
            style={{ opacity: "0.7" }}
            onClick={async () => {
              await window.electronAPI.updateUserSettings(
                "show_splash_screen",
                false
              );
              onComplete();
            }}
          >
            <i>Don't show this screen on startup</i>
          </button>
          <button
            className="call-to-action-2"
            text-style="display"
            onClick={() => onComplete()}
          >
            Close
          </button>
        </div>
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
          fileName={() => ""}
        />
      </GenericModal>
    </>
  );
}

export default SplashScreen;
