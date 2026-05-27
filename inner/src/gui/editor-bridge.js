// Browser-side bridge that exposes the editor pywebview js_api on
// ``window.editorAPI`` and waits for the bridge to populate before
// invoking. The editor window is hosted by the inner Symphony
// process (``inner/src/main.py``) and registers the methods declared
// in ``inner/src/editor/editor_api.py`` on ``window.pywebview.api``.
//
// The names mirror the backend dispatcher surface: document state,
// note edits, metadata/settings, audio playback, transactions, and
// the temp-note drag list. The frontend remains a stub for now;
// these handlers exist so future React surfaces can wire UI events
// to the backend without re-implementing the bridge.

const READY_TIMEOUT_MS = 10000;

let _pywebviewReady = false;
if (typeof window !== "undefined") {
  window.addEventListener("pywebviewready", () => {
    _pywebviewReady = true;
  });
}

function isBridgePopulated() {
  if (!window.pywebview || !window.pywebview.api) return false;
  if (_pywebviewReady) return true;
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
        reject(new Error("editor pywebview bridge timeout"));
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
    throw new Error(`editor pywebview API missing method: ${method}`);
  });
}

// Editor state event fan-out. The Python side calls
// ``window.__symphony_editor_state(state)`` whenever the document
// snapshot changes (load, undo, redo, channel/wave change, etc).
const editorStateListeners = new Set();
window.__symphony_editor_state = (state) => {
  editorStateListeners.forEach((cb) => {
    try {
      cb(state);
    } catch (err) {
      console.error("editor-state listener failed:", err);
    }
  });
};

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

const editorAPI = {
  // ---- platform / window controls -------------------------------------
  getPlatform: () => call("getPlatform"),
  minimize: () => call("minimize"),
  maximize: () => call("maximize"),
  close: () => call("close"),
  toggleDevTools: () => call("toggleDevtools"),
  openExternalUrl: (url) => call("openExternalUrl", url),
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

  // ---- document state -------------------------------------------------
  getDocumentState: () => call("getDocumentState"),
  saveNow: () => call("saveNow"),
  onEditorStateChange: (callback) => {
    editorStateListeners.add(callback);
    return () => editorStateListeners.delete(callback);
  },

  // ---- note edits -----------------------------------------------------
  drawNote: (color, note) => call("drawNote", color, note),
  eraseNoteAt: (color, time, pitch) => call("eraseNoteAt", color, time, pitch),
  setSelection: (selection) => call("setSelection", selection),
  clearSelection: () => call("clearSelection"),
  deleteSelectedNotes: () => call("deleteSelectedNotes"),

  // ---- metadata / settings -------------------------------------------
  setAccidentals: (mode) => call("setAccidentals", mode),
  setBeatLength: (value) => call("setBeatLength", value),
  setBeatsPerMeasure: (value) => call("setBeatsPerMeasure", value),
  setTempo: (tpm) => call("setTempo", tpm),
  setKey: (key) => call("setKey", key),
  setMode: (mode) => call("setMode", mode),
  setActiveColor: (colorIdx) => call("setActiveColor", colorIdx),
  setWaveType: (color, waveIdx) => call("setWaveType", color, waveIdx),
  updateProjectMetadata: (metadata) => call("updateProjectMetadata", metadata),

  // ---- audio playback -------------------------------------------------
  playNotePreview: (pitch, color) => call("playNotePreview", pitch, color),
  playPitch: (pitch) => call("playPitch", pitch),
  playFull: (options) => call("playFull", options || {}),
  stopPlayback: () => call("stopPlayback"),
  setPlayheadHome: (time) => call("setPlayheadHome", time),

  // ---- transactions ---------------------------------------------------
  undo: () => call("undo"),
  redo: () => call("redo"),

  // ---- temp drag list -------------------------------------------------
  beginTempNotes: (action, color, originals) =>
    call("beginTempNotes", action, color, originals),
  appendTempNotes: (notes) => call("appendTempNotes", notes),
  setTempNotes: (notes) => call("setTempNotes", notes),
  commitTempNotes: () => call("commitTempNotes"),
  cancelTempNotes: () => call("cancelTempNotes"),
};

if (typeof window !== "undefined" && !window.editorAPI) {
  window.editorAPI = editorAPI;
}

export default editorAPI;
