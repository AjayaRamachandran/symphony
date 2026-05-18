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
  onWindowStateChange: (callback) => {
    windowStateListeners.add(callback);
    return () => windowStateListeners.delete(callback);
  },

  // File ops
  startFileDrag: (filePath, event) => {
    // PyWebview can't drive a native OS drag from JS. Best-effort: attach the
    // HTML5 ``DownloadURL`` data so Chromium-based webviews (incl. WebView2)
    // can drop the file onto Explorer/Finder. The caller must NOT have already
    // called event.preventDefault().
    try {
      if (event && event.dataTransfer && filePath) {
        const name = filePath.split(/[\\/]/).pop();
        const fileUrl = "file:///" + filePath.replace(/\\/g, "/").replace(/^\/+/, "");
        event.dataTransfer.effectAllowed = "copyMove";
        event.dataTransfer.setData(
          "DownloadURL",
          `application/octet-stream:${name}:${fileUrl}`
        );
        event.dataTransfer.setData("text/uri-list", fileUrl);
        event.dataTransfer.setData("text/plain", filePath);
      }
    } catch (err) {
      console.warn("startFileDrag DownloadURL setup failed:", err);
    }
    // Fire-and-forget; Python side is a no-op but keeps API parity.
    call("startFileDrag", filePath).catch(() => {});
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
  openEditorProgram: () => call("openEditorProgram"),
  doProcessCommand: (symphonyFilePath, command, extraArgs) =>
    call("doProcessCommand", symphonyFilePath, command, extraArgs || {}),
};

if (typeof window !== "undefined" && !window.electronAPI) {
  window.electronAPI = electronAPI;
}

export default electronAPI;
