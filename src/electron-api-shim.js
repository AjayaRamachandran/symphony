// Browser-side shim that re-exposes the legacy ``window.electronAPI`` surface
// on top of pywebview's ``window.pywebview.api``. Imported first in
// ``src/main.jsx`` so the rest of the React app can call electronAPI as before.
//
// Notes:
//  - Every Python-backed call returns a Promise. pywebview snake_cases method
//    names; we wrap each one in a small helper that waits for the bridge to be
//    ready before invoking.
//  - Window-state events come back from Python via
//    ``window.__symphony_emit_window_state(bool)`` which fans out to all
//    registered ``onWindowStateChange`` listeners.

const READY_TIMEOUT_MS = 10000;
const RESIZE_HANDLE_WIDTH = 10;
const TITLE_BAR_HEIGHT = 30;
const WINDOW_BUTTONS_WIDTH = 108;

// pywebview initializes ``window.pywebview.api`` as an empty {} early, then
// populates the function members and fires ``pywebviewready``. Resolving on
// the bare object presence races with method registration, so we additionally
// require either the ready event or a populated api object.
let _pywebviewReady = false;
if (typeof window !== "undefined") {
  window.addEventListener("pywebviewready", () => {
    _pywebviewReady = true;
  });
}

function isBridgePopulated() {
  if (!window.pywebview || !window.pywebview.api) return false;
  if (_pywebviewReady) return true;
  // Fallback heuristic: any registered function indicates _createApi ran.
  for (const k in window.pywebview.api) {
    if (typeof window.pywebview.api[k] === "function") return true;
  }
  return false;
}

let readyPromise = null;
function waitForBridge() {
  if (readyPromise) return readyPromise;
  readyPromise = new Promise((resolve, reject) => {
    if (isBridgePopulated()) {
      resolve(window.pywebview.api);
      return;
    }
    const start = Date.now();
    const poll = () => {
      if (isBridgePopulated()) {
        resolve(window.pywebview.api);
        return;
      }
      if (Date.now() - start > READY_TIMEOUT_MS) {
        reject(new Error("pywebview bridge timeout"));
        return;
      }
      setTimeout(poll, 50);
    };
    window.addEventListener("pywebviewready", () => {
      if (isBridgePopulated()) resolve(window.pywebview.api);
    });
    poll();
  });
  return readyPromise;
}

function camelToSnake(name) {
  return name.replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());
}

function call(method, ...args) {
  return waitForBridge().then((api) => {
    const candidates = [method, camelToSnake(method)];
    for (const key of candidates) {
      const fn = api[key];
      if (typeof fn === "function") {
        return fn.apply(api, args);
      }
    }
    throw new Error(`pywebview API missing method: ${method}`);
  });
}

// ---- platform detection (sync, derived from navigator) --------------------
function detectPlatform() {
  const plat = (navigator.platform || "").toLowerCase();
  const ua = (navigator.userAgent || "").toLowerCase();
  if (plat.includes("mac") || ua.includes("mac os")) return "darwin";
  if (plat.includes("win") || ua.includes("windows")) return "win32";
  return "linux";
}

// ---- native OS file drop dispatcher ---------------------------------------
// Called from Python (main.py emitNativeDrop) when the host HWND or NSWindow
// receives an external file drop. Re-broadcasts as a CustomEvent so any drop
// zone in the React tree can subscribe with a single ``window.addEventListener``
// instead of polling the bridge. The timestamp helps HTML5 ``drop`` handlers
// debounce themselves so a single OS gesture is not handled twice.
window.__symphonyLastNativeDrop = 0;
window.__symphonyNativeDrop = (payload) => {
  try {
    const detail = payload && typeof payload === "object" ? payload : {};
    console.log("[symphony-drag] native drop received", detail);
    window.__symphonyLastNativeDrop = Date.now();
    window.dispatchEvent(
      new CustomEvent("symphony:native-drop", { detail }),
    );
  } catch (err) {
    console.error("[symphony-drag] __symphonyNativeDrop dispatch failed:", err);
  }
};

// ---- window-state event fanout --------------------------------------------
const windowStateListeners = new Set();
window.__symphony_emit_window_state = (isMaximized) => {
  windowStateListeners.forEach((cb) => {
    try {
      cb(isMaximized);
    } catch (err) {
      console.error("window-state listener failed:", err);
    }
  });
};

// ---- drag-region setup ----------------------------------------------------
// pywebview's customize.js runs querySelectorAll('.pywebview-drag-region') at
// inject-time. React's deferred module script may mount the titlebar after
// that snapshot, so we attach our own handler that walks current DOM matches.
function setupDragRegions() {
  const attach = (el) => {
    if (el.__symphonyDragAttached) return;
    el.__symphonyDragAttached = true;
    let initialX = 0;
    let initialY = 0;
    const onMove = (ev) => {
      const x = ev.screenX - initialX;
      const y = ev.screenY - initialY;
      try {
        window.pywebview._jsApiCallback("pywebviewMoveWindow", [x, y], "move");
      } catch (err) {
        /* ignore */
      }
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    el.addEventListener("mousedown", (ev) => {
      if (ev.button !== 0) return;
      initialX = ev.clientX;
      initialY = ev.clientY;
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    });
  };
  document.querySelectorAll(".pywebview-drag-region").forEach(attach);
}

function initDragRegions() {
  setupDragRegions();
  const observer = new MutationObserver(() => setupDragRegions());
  observer.observe(document.body, { childList: true, subtree: true });
}

if (typeof window !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDragRegions);
  } else {
    initDragRegions();
  }
}

// ---- frameless resize handles ---------------------------------------------
// WebView2 (win) and WKWebView (mac) both own the child view under the cursor,
// so top-level hit-testing does not reliably see edge mouse-downs. These
// transparent DOM handles drive the manual resize path on Python's side, which
// dispatches to win_c_man on Windows and mac_w_man on macOS.
function setupResizeHandles() {
  const platform = detectPlatform();
  if (platform !== "win32" && platform !== "darwin") return;
  if (document.getElementById("symphony-resize-handles")) return;

  const root = document.createElement("div");
  root.id = "symphony-resize-handles";
  root.setAttribute("aria-hidden", "true");

  const base = {
    position: "fixed",
    zIndex: "2147483647",
    background: "transparent",
    pointerEvents: "auto",
    userSelect: "none",
  };

  const handles = [
    {
      edge: "top",
      cursor: "ns-resize",
      style: {
        top: "0",
        left: `${RESIZE_HANDLE_WIDTH}px`,
        right: `${WINDOW_BUTTONS_WIDTH}px`,
        height: `${RESIZE_HANDLE_WIDTH}px`,
      },
    },
    {
      edge: "bottom",
      cursor: "ns-resize",
      style: {
        left: `${RESIZE_HANDLE_WIDTH}px`,
        right: `${RESIZE_HANDLE_WIDTH}px`,
        bottom: "0",
        height: `${RESIZE_HANDLE_WIDTH}px`,
      },
    },
    {
      edge: "left",
      cursor: "ew-resize",
      style: { top: "0", bottom: "0", left: "0", width: `${RESIZE_HANDLE_WIDTH}px` },
    },
    {
      edge: "right",
      cursor: "ew-resize",
      style: {
        top: `${TITLE_BAR_HEIGHT}px`,
        bottom: "0",
        right: "0",
        width: `${RESIZE_HANDLE_WIDTH}px`,
      },
    },
    {
      edge: "top-left",
      cursor: "nwse-resize",
      style: {
        top: "0",
        left: "0",
        width: `${RESIZE_HANDLE_WIDTH}px`,
        height: `${RESIZE_HANDLE_WIDTH}px`,
      },
    },
    {
      edge: "bottom-left",
      cursor: "nesw-resize",
      style: {
        bottom: "0",
        left: "0",
        width: `${RESIZE_HANDLE_WIDTH}px`,
        height: `${RESIZE_HANDLE_WIDTH}px`,
      },
    },
    {
      edge: "bottom-right",
      cursor: "nwse-resize",
      style: {
        bottom: "0",
        right: "0",
        width: `${RESIZE_HANDLE_WIDTH}px`,
        height: `${RESIZE_HANDLE_WIDTH}px`,
      },
    },
  ];

  for (const handle of handles) {
    const el = document.createElement("div");
    Object.assign(el.style, base, handle.style, { cursor: handle.cursor });
    el.addEventListener("mousedown", (ev) => {
      if (ev.button !== 0) return;
      ev.preventDefault();
      ev.stopPropagation();

      let pending = false;
      let latestX = ev.screenX;
      let latestY = ev.screenY;

      const flushResize = () => {
        if (pending) return;
        pending = true;
        call("updateManualWindowResize", latestX, latestY)
          .catch((err) => {
            console.warn("updateManualWindowResize failed:", err);
          })
          .finally(() => {
            pending = false;
          });
      };

      const onMove = (moveEv) => {
        latestX = moveEv.screenX;
        latestY = moveEv.screenY;
        window.requestAnimationFrame(flushResize);
      };

      const onUp = () => {
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        call("endManualWindowResize").catch(() => {});
      };

      call("beginManualWindowResize", handle.edge, ev.screenX, ev.screenY)
        .then((started) => {
          if (!started) {
            return call("startWindowResize", handle.edge);
          }
          window.addEventListener("mousemove", onMove);
          window.addEventListener("mouseup", onUp);
        })
        .catch((err) => {
          console.warn("beginManualWindowResize failed:", err);
          call("startWindowResize", handle.edge).catch(() => {});
        });
    });
    root.appendChild(el);
  }

  document.body.appendChild(root);
}

function initResizeHandles() {
  setupResizeHandles();
  const observer = new MutationObserver(() => setupResizeHandles());
  observer.observe(document.body, { childList: true });
}

if (typeof window !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initResizeHandles);
  } else {
    initResizeHandles();
  }
}

// ---- ArrayBuffer -> base64 (for moveFileRaw) ------------------------------
function arrayBufferToBase64(buffer) {
  if (!buffer) return "";
  if (typeof buffer === "string") return buffer;
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(
      null,
      bytes.subarray(i, Math.min(i + chunk, bytes.length))
    );
  }
  return btoa(binary);
}

// PyWebview 5.x exposes Python snake_case method names as camelCase on the JS
// side, so all method names below use camelCase to match.
const electronAPI = {
  // Synchronous-looking platform (matches old preload semantics).
  platform: detectPlatform(),
  isPywebview: true,

  // Window controls
  minimize: () => call("minimize"),
  maximize: () => call("maximize"),
  close: () => call("close"),
  toggleDevTools: () => call("toggleDevtools"),
  startWindowResize: (edge) => call("startWindowResize", edge),
  beginManualWindowResize: (edge, screenX, screenY) =>
    call("beginManualWindowResize", edge, screenX, screenY),
  updateManualWindowResize: (screenX, screenY) =>
    call("updateManualWindowResize", screenX, screenY),
  endManualWindowResize: () => call("endManualWindowResize"),
  onWindowStateChange: (callback) => {
    windowStateListeners.add(callback);
    return () => windowStateListeners.delete(callback);
  },

  // File ops
  startFileDrag: (filePath, event) => {
    // Populate the HTML5 drag payload as a fallback for in-WebView drop
    // targets (file grid, sidebar folders). The Python side runs the real
    // native shell drag on the WebView's UI thread (Win32 PostMessageW +
    // WndProc DoDragDrop, or dispatch-to-main on macOS) so OS targets like
    // Explorer / Finder / Discord receive a real CF_HDROP / file URL.
    console.log("[symphony-drag] shim.startFileDrag", {
      filePath,
      hasEvent: Boolean(event),
      hasDataTransfer: Boolean(event && event.dataTransfer),
    });
    try {
      if (event && event.dataTransfer && filePath) {
        const name = filePath.split(/[\\/]/).pop();
        const fileUrl =
          "file:///" + filePath.replace(/\\/g, "/").replace(/^\/+/, "");
        event.dataTransfer.effectAllowed = "copyMove";
        event.dataTransfer.setData(
          "DownloadURL",
          `application/octet-stream:${name}:${fileUrl}`,
        );
        event.dataTransfer.setData("text/uri-list", fileUrl);
        event.dataTransfer.setData("text/plain", filePath);
      }
    } catch (err) {
      console.warn("[symphony-drag] DownloadURL setup failed:", err);
    }
    if (filePath) {
      call("startFileDrag", filePath).catch((err) =>
        console.warn("[symphony-drag] native drag failed:", err),
      );
    }
  },
  openExternal: (url) => call("openExternal", url),
  openFileLocation: (filePath) => call("openFileLocation", filePath),
  fileExists: (filePath) => call("fileExists", filePath),
  deleteFile: (filePath) => call("deleteFile", filePath),
  renameFile: (filePath, newName) =>
    call("renameFile", { filePath, newName }),
  copyFile: (src, dest) => call("copyFile", src, dest),
  moveFileRaw: (fileBuffer, fileName, destinationDir, originalFilePath) =>
    call(
      "moveFileRaw",
      arrayBufferToBase64(fileBuffer),
      fileName,
      destinationDir,
      originalFilePath || null
    ),
  copyPathsInto: (paths, destinationDir) =>
    call("copyPathsInto", Array.isArray(paths) ? paths : [paths], destinationDir),

  // Directory ops
  openDirectory: () => call("openDirectory"),
  saveDirectory: (data) => call("saveDirectory", data),
  getDirectory: () => call("getDirectory"),
  removeDirectory: (section, dirName) =>
    call("removeDirectory", section, dirName),
  getSectionForPath: (filePath) => call("getSectionForPath", filePath),
  checkIfExists: (data) => call("checkIfExists", data),

  // Recently viewed
  getRecentlyViewed: () => call("getRecentlyViewed"),
  recentlyViewedDelete: (fileName, fileLocation) =>
    call("recentlyViewedDelete", fileName, fileLocation || null),
  clearRecentlyViewed: () => call("clearRecentlyViewed"),

  // Stars
  getStars: () => call("getStars"),
  addStar: (filePath) => call("addStar", filePath),
  removeStar: (filePath) => call("removeStar", filePath),

  // User settings + misc
  getUserSettings: () => call("getUserSettings"),
  updateUserSettings: (key, value) => call("updateUserSettings", key, value),
  fetchJson: (url, options) => call("fetchJson", url, options || {}),

  // Symphony files / editor
  getSymphonyFiles: (directoryPath) => call("getSymphonyFiles", directoryPath),
  openNativeApp: (filePath) => call("openNativeApp", filePath),
  runEditorProgram: () => call("runEditorProgram"),
  doProcessCommand: (symphonyFilePath, command, extraArgs) =>
    call("doProcessCommand", symphonyFilePath, command, extraArgs || {}),
};

if (typeof window !== "undefined" && !window.electronAPI) {
  window.electronAPI = electronAPI;
}

export default electronAPI;
