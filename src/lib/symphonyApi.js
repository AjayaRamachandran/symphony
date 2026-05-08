// Neutralino-backed implementation of the API formerly exposed by
// preload.js as `window.electronAPI`. This file is the single source of
// truth for native operations the renderer needs (filesystem, window
// controls, dialogs, spawning the Python editor, etc.).
//
// The interface is preserved so existing components keep calling
// `window.electronAPI.*` without modification.

import * as Neutralino from "@neutralinojs/lib";
import path from "path-browserify";

import { startEditor, doProcessCommand } from "./editorProcess";

const DEFAULT_SETTINGS = {
  needs_onboarding: true,
  search_for_updates: true,
  show_splash_screen: true,
  user_name: "",
  fancy_graphics: true,
  show_console: false,
  disable_auto_save: false,
  disable_delete_confirm: false,
  show_button_tooltips: true,
  clef_presets: {},
};

const RETIRED_SETTING_KEYS = ["close_project_manager_when_editing"];

let dataPathPromise = null;
let appPathsPromise = null;

function nlOsToNodePlatform(nlOs) {
  switch (nlOs) {
    case "Darwin":
      return "darwin";
    case "Windows":
      return "win32";
    case "Linux":
      return "linux";
    case "FreeBSD":
      return "freebsd";
    default:
      return String(nlOs || "").toLowerCase();
  }
}

async function pathExists(p) {
  try {
    await Neutralino.filesystem.getStats(p);
    return true;
  } catch {
    return false;
  }
}

async function ensureDir(dirPath) {
  if (!(await pathExists(dirPath))) {
    try {
      await Neutralino.filesystem.createDirectory(dirPath);
    } catch (err) {
      if (!(await pathExists(dirPath))) throw err;
    }
  }
}

async function readJson(filePath, fallback) {
  try {
    const text = await Neutralino.filesystem.readFile(filePath);
    return JSON.parse(text);
  } catch {
    return fallback;
  }
}

async function writeJson(filePath, value) {
  await Neutralino.filesystem.writeFile(filePath, JSON.stringify(value, null, 2));
}

async function readBinaryAsArrayBuffer(filePath) {
  return Neutralino.filesystem.readBinaryFile(filePath);
}

// Data path: equivalent to Electron's app.getPath('userData').
// Resolves to <os data dir>/Symphony so a clean reinstall under
// Neutralino picks up the same user data Electron used on Windows
// (%APPDATA%/Symphony) and macOS (~/Library/Application Support/Symphony).
function getDataPath() {
  if (!dataPathPromise) {
    dataPathPromise = (async () => {
      const base = await Neutralino.os.getPath("data");
      const dir = `${base.replace(/[\\/]+$/, "")}/Symphony`;
      await ensureDir(dir);
      return dir;
    })();
  }
  return dataPathPromise;
}

function getAppPaths() {
  if (!appPathsPromise) {
    appPathsPromise = (async () => {
      const dataDir = await getDataPath();
      return {
        dataDir,
        directoryFile: `${dataDir}/directory.json`,
        recentlyViewedFile: `${dataDir}/recently-viewed.json`,
        starredFile: `${dataDir}/starred.json`,
        userSettingsFile: `${dataDir}/user-settings.json`,
        processCommandFile: `${dataDir}/process-command.json`,
      };
    })();
  }
  return appPathsPromise;
}

async function ensureSeedFiles() {
  const paths = await getAppPaths();
  const seeds = [
    [paths.userSettingsFile, DEFAULT_SETTINGS],
    [paths.directoryFile, { Projects: [], Exports: [], "Symphony Auto-Save": [] }],
    [paths.starredFile, []],
    [paths.recentlyViewedFile, []],
  ];
  for (const [file, defaults] of seeds) {
    if (!(await pathExists(file))) {
      try {
        await writeJson(file, defaults);
      } catch (err) {
        console.error("Failed to seed", file, err);
      }
    }
  }
}

async function deleteFileWithMetadata(filePath) {
  try {
    await Neutralino.filesystem.remove(filePath);
    const metadataPath = filePath.replace(/\.symphony$/i, ".json");
    if (metadataPath !== filePath && (await pathExists(metadataPath))) {
      await Neutralino.filesystem.remove(metadataPath);
    }
    return { success: true };
  } catch (err) {
    return { success: false, error: err?.message || String(err) };
  }
}

async function filesAreSameSize(a, b) {
  try {
    const [aStats, bStats] = await Promise.all([
      Neutralino.filesystem.getStats(a),
      Neutralino.filesystem.getStats(b),
    ]);
    return aStats.size === bStats.size;
  } catch {
    return false;
  }
}

async function fetchJson(url, options = {}) {
  const parsed = new URL(url);
  if (!["http:", "https:"].includes(parsed.protocol)) {
    return { success: false, error: `Unsupported protocol: ${parsed.protocol}` };
  }
  try {
    const response = await fetch(url, {
      method: options.method || "GET",
      headers: options.headers || {},
      body: options.body,
    });
    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` };
    }
    return { success: true, data: await response.json() };
  } catch (err) {
    return { success: false, error: err?.message || String(err) };
  }
}

async function addRecentlyViewed(filePath) {
  if (!filePath) return;
  const paths = await getAppPaths();
  let recent = [];
  if (await pathExists(paths.recentlyViewedFile)) {
    recent = (await readJson(paths.recentlyViewedFile, [])) || [];
  }
  const fileName = path.basename(filePath);
  const fileType = path.extname(fileName).replace(".", "").toLowerCase();
  const entry = { type: fileType, name: fileName, fileLocation: path.dirname(filePath) };
  recent = recent.filter(
    (r) => !(r.name === entry.name && r.fileLocation === entry.fileLocation),
  );
  recent.unshift(entry);
  if (recent.length > 15) recent = recent.slice(0, 15);
  await writeJson(paths.recentlyViewedFile, recent);
}

const VALID_FILE_EXTS = new Set([
  ".symphony",
  ".wav",
  ".mid",
  ".mp3",
  ".flac",
  ".musicxml",
]);

let cachedPlatform = "";

export async function initSymphonyApi() {
  const nlOs = typeof NL_OS !== "undefined" ? NL_OS : "";
  cachedPlatform = nlOsToNodePlatform(nlOs);

  await getAppPaths();
  await ensureSeedFiles();

  const paths = await getAppPaths();
  const editorOptions = await resolveEditorOptions();
  await startEditor({ ...editorOptions, processCommandPath: paths.processCommandFile });

  Neutralino.events.on("windowClose", async () => {
    try {
      await doProcessCommand("", "kill", {});
    } catch (err) {
      console.error("Failed to send kill on close:", err);
    } finally {
      Neutralino.app.exit();
    }
  });
}

async function resolveEditorOptions() {
  const cwd = typeof NL_CWD !== "undefined" ? NL_CWD : "";
  const appPath = typeof NL_PATH !== "undefined" ? NL_PATH : cwd;
  const platform = cachedPlatform;

  // Read editorIsExe preference from config.yaml (defaults to false to
  // match the historical Electron behaviour).
  let editorIsExe = false;
  try {
    const text = await Neutralino.filesystem.readFile(`${appPath}/config.yaml`);
    if (/editorIsExe\s*:\s*true/i.test(text)) editorIsExe = true;
  } catch {}

  // Candidate locations, in priority order. We prefer the Python source
  // (matches the user's `editorIsExe: false` preference) and fall back
  // to the bundled binary so a packaged build still has a working
  // editor without Python installed.
  const exeName = platform === "win32" ? "main.exe" : "main";
  const candidates = editorIsExe
    ? [
        { dir: `${appPath}/inner/dist`, file: exeName, isPython: false },
        { dir: `${appPath}/inner/src`, file: "main.py", isPython: true },
      ]
    : [
        { dir: `${appPath}/inner/src`, file: "main.py", isPython: true },
        { dir: `${appPath}/inner/dist`, file: "main.py", isPython: true },
        { dir: `${appPath}/inner/dist`, file: exeName, isPython: false },
      ];

  for (const c of candidates) {
    const fullPath = `${c.dir}/${c.file}`;
    if (await pathExists(fullPath)) {
      return {
        platform,
        isDev: c.isPython && c.dir.endsWith("/inner/src"),
        innerDistPath: c.dir,
        executablePath: fullPath,
        isPythonScript: c.isPython,
      };
    }
  }

  console.warn("[symphony] No editor binary found near", appPath);
  return {
    platform,
    isDev: false,
    innerDistPath: `${appPath}/inner/dist`,
    executablePath: `${appPath}/inner/dist/${exeName}`,
    isPythonScript: false,
  };
}

export const symphonyAPI = {
  // Window Controls
  get platform() {
    return cachedPlatform;
  },
  minimize: () => Neutralino.window.minimize(),
  maximize: async () => {
    const isMax = await Neutralino.window.isMaximized();
    if (isMax) await Neutralino.window.unmaximize();
    else await Neutralino.window.maximize();
  },
  close: async () => {
    try {
      await doProcessCommand("", "kill", {});
    } catch (err) {
      console.error("Failed to send kill on close:", err);
    } finally {
      Neutralino.app.exit();
    }
  },
  onWindowStateChange: (callback) => {
    Neutralino.events.on("windowMaximize", () => callback(true));
    Neutralino.events.on("windowRestore", () => callback(false));
    Neutralino.events.on("windowUnmaximize", () => callback(false));
  },
  toggleDevTools: () => {
    // Neutralino exposes the inspector via the `enableInspector` config
    // flag and the `--window-enable-inspector` CLI argument. There is no
    // runtime toggle; right-click -> Inspect inside the window when the
    // inspector is enabled.
    console.log("[symphony] DevTools toggle requested (use right-click -> Inspect).");
  },

  // File Operations
  startFileDrag: () => {
    // Electron's webContents.startDrag() lets a user drag a file out of
    // the window onto the OS desktop. Neutralino doesn't have a native
    // equivalent yet; in-app drag-and-drop still works because the
    // renderer tracks the dragging path via DirectoryContext.
  },
  openExternal: (url) => Neutralino.os.open(url),
  openFileLocation: async (filePath) => {
    const folder = path.dirname(filePath);
    let command;
    if (cachedPlatform === "win32") {
      command = `explorer "${folder.replace(/\//g, "\\")}"`;
    } else if (cachedPlatform === "darwin") {
      command = `open "${folder}"`;
    } else {
      command = `xdg-open "${folder}"`;
    }
    try {
      await Neutralino.os.execCommand(command, { background: true });
      return true;
    } catch (err) {
      console.error("Failed to open file location:", err);
      return false;
    }
  },
  fileExists: async (filePath) => pathExists(filePath),
  deleteFile: async (filePath) => deleteFileWithMetadata(filePath),
  renameFile: async ({ filePath, newName }) => {
    const dir = path.dirname(filePath);
    let baseName = newName;
    let ext = path.extname(newName);
    if (!ext) ext = ".symphony";
    let candidate = baseName + ext;
    let counter = 1;
    let entries = [];
    try {
      entries = await Neutralino.filesystem.readDirectory(dir);
    } catch {}
    const existing = new Set(entries.map((e) => e.entry));
    while (existing.has(candidate)) {
      candidate = `${baseName} (${counter})${ext}`;
      counter++;
    }
    try {
      const newFilePath = `${dir}/${candidate}`;
      await Neutralino.filesystem.move(filePath, newFilePath);
      const originalJsonPath = filePath.replace(/\.symphony$/i, ".json");
      const newJsonPath = newFilePath.replace(/\.symphony$/i, ".json");
      if (
        originalJsonPath !== filePath &&
        (await pathExists(originalJsonPath))
      ) {
        await Neutralino.filesystem.move(originalJsonPath, newJsonPath);
      }
      return { success: true, newFilePath };
    } catch (err) {
      return { success: false, error: err?.message || String(err) };
    }
  },
  copyFile: async (src, dest) => {
    await Neutralino.filesystem.copy(src, dest);
    return "success";
  },
  moveFileRaw: async (arrayBuffer, fileName, destinationDir, originalFilePath) => {
    const destPath = `${destinationDir.replace(/[\\/]+$/, "")}/${fileName}`;
    try {
      await Neutralino.filesystem.writeBinaryFile(destPath, arrayBuffer);
      let deletedOriginal = false;
      if (originalFilePath) {
        const same =
          originalFilePath.replace(/\\/g, "/") === destPath.replace(/\\/g, "/");
        if (same) return { success: true, deletedOriginal: false };
        if (await filesAreSameSize(originalFilePath, destPath)) {
          const result = await deleteFileWithMetadata(originalFilePath);
          deletedOriginal = !!result?.success;
        }
      }
      return { success: true, deletedOriginal };
    } catch (err) {
      return { success: false, error: err?.message || String(err) };
    }
  },

  // Directory Operations
  openDirectory: async () => {
    try {
      const folder = await Neutralino.os.showFolderDialog("Choose a folder");
      return folder || null;
    } catch (err) {
      console.error(err);
      return null;
    }
  },
  saveDirectory: async ({ destination, projectName, sourceLocation }) => {
    const paths = await getAppPaths();
    try {
      const directory = (await readJson(paths.directoryFile, {})) || {};
      if (!directory[destination]) directory[destination] = [];
      const nameExists = directory[destination].some((e) => e[projectName]);
      const locationExists = directory[destination].some((e) =>
        Object.values(e).includes(sourceLocation),
      );
      if (nameExists || locationExists) {
        return { success: false, error: "Duplicate entry" };
      }
      directory[destination].push({ [projectName]: sourceLocation });
      await writeJson(paths.directoryFile, directory);
      return { success: true };
    } catch (err) {
      return { success: false, error: err?.message || String(err) };
    }
  },
  getDirectory: async () => {
    const paths = await getAppPaths();
    if (!(await pathExists(paths.directoryFile))) {
      const def = { Projects: [], Exports: [], "Symphony Auto-Save": [] };
      await writeJson(paths.directoryFile, def);
      return def;
    }
    return readJson(paths.directoryFile, {});
  },
  removeDirectory: async (section, dirName) => {
    const paths = await getAppPaths();
    if (!(await pathExists(paths.directoryFile))) {
      return { success: false, error: "directory.json not found" };
    }
    try {
      const directory = (await readJson(paths.directoryFile, {})) || {};
      if (!directory[section]) {
        return { success: false, error: "Section not found" };
      }
      directory[section] = directory[section].filter(
        (obj) => Object.keys(obj)[0] !== dirName,
      );
      await writeJson(paths.directoryFile, directory);
      return { success: true };
    } catch (err) {
      return { success: false, error: err?.message || String(err) };
    }
  },
  getSectionForPath: async (filePath) => {
    const paths = await getAppPaths();
    if (!(await pathExists(paths.directoryFile))) {
      return { error: "Directory data not found." };
    }
    try {
      const directoryData = (await readJson(paths.directoryFile, {})) || {};
      const target = filePath.replace(/\\/g, "/");
      for (const [section, entries] of Object.entries(directoryData)) {
        for (const entry of entries) {
          const folderPath = Object.values(entry)[0];
          if (folderPath.replace(/\\/g, "/") === target) {
            return { section };
          }
        }
      }
      return { section: null, message: "Path not found in any section." };
    } catch (err) {
      return { error: err?.message || String(err) };
    }
  },
  checkIfExists: async ({ destination, projectName, sourceLocation }) => {
    const paths = await getAppPaths();
    try {
      const directory = (await readJson(paths.directoryFile, {})) || {};
      if (!directory[destination]) return { success: true };
      const entries = directory[destination] || [];
      const nameCount = entries.filter((e) => e[projectName] !== undefined).length;
      const locationCount = entries.filter((e) =>
        Object.values(e).includes(sourceLocation),
      ).length;
      const isDuplicate = nameCount > 0 || locationCount > 0;
      return { success: isDuplicate };
    } catch {
      return { success: false };
    }
  },

  // Recently Viewed
  getRecentlyViewed: async () => {
    const paths = await getAppPaths();
    if (!(await pathExists(paths.recentlyViewedFile))) {
      await writeJson(paths.recentlyViewedFile, []);
    }
    return (await readJson(paths.recentlyViewedFile, [])) || [];
  },
  recentlyViewedDelete: async (fileName, fileLocation = null) => {
    const paths = await getAppPaths();
    if (!(await pathExists(paths.recentlyViewedFile))) {
      return { success: false, error: "recently-viewed.json not found" };
    }
    try {
      let recent = (await readJson(paths.recentlyViewedFile, [])) || [];
      const before = recent.length;
      recent = recent.filter((item) => {
        if (fileLocation) {
          return !(item.name === fileName && item.fileLocation === fileLocation);
        }
        return item.name !== fileName;
      });
      if (recent.length === before) {
        return { success: false, error: "Entry not found" };
      }
      await writeJson(paths.recentlyViewedFile, recent);
      return { success: true };
    } catch (err) {
      return { success: false, error: err?.message || String(err) };
    }
  },
  clearRecentlyViewed: async () => {
    const paths = await getAppPaths();
    try {
      await writeJson(paths.recentlyViewedFile, []);
      return { success: true };
    } catch (err) {
      return { success: false, error: err?.message || String(err) };
    }
  },

  // Starred Files
  getStars: async () => {
    const paths = await getAppPaths();
    if (!(await pathExists(paths.starredFile))) {
      await writeJson(paths.starredFile, []);
    }
    return (await readJson(paths.starredFile, [])) || [];
  },
  addStar: async (filePath) => {
    const paths = await getAppPaths();
    try {
      if (!(await pathExists(paths.starredFile))) {
        await writeJson(paths.starredFile, []);
      }
      const stars = (await readJson(paths.starredFile, [])) || [];
      const normalized = filePath.replace(/\\/g, "/");
      const already = stars.some((s) => s.replace(/\\/g, "/") === normalized);
      if (!already) {
        stars.push(filePath);
        await writeJson(paths.starredFile, stars);
      }
      return stars;
    } catch (err) {
      console.error(err);
      return [];
    }
  },
  removeStar: async (filePath) => {
    const paths = await getAppPaths();
    try {
      if (!(await pathExists(paths.starredFile))) {
        await writeJson(paths.starredFile, []);
      }
      let stars = (await readJson(paths.starredFile, [])) || [];
      const target = filePath.replace(/\\/g, "/");
      stars = stars.filter((s) => s.replace(/\\/g, "/") !== target);
      await writeJson(paths.starredFile, stars);
      return stars;
    } catch {
      return [];
    }
  },

  // User Settings
  getUserSettings: async () => {
    const paths = await getAppPaths();
    try {
      let userSettings = {};
      if (await pathExists(paths.userSettingsFile)) {
        userSettings = (await readJson(paths.userSettingsFile, {})) || {};
      }
      const sanitized = { ...userSettings };
      for (const key of RETIRED_SETTING_KEYS) delete sanitized[key];
      const updated = { ...DEFAULT_SETTINGS, ...sanitized };
      await writeJson(paths.userSettingsFile, updated);
      return updated;
    } catch (err) {
      console.error("Error reading or updating user settings:", err);
      return { ...DEFAULT_SETTINGS };
    }
  },
  updateUserSettings: async (key, value) => {
    const paths = await getAppPaths();
    try {
      const settings = (await readJson(paths.userSettingsFile, {})) || {};
      settings[key] = value;
      await writeJson(paths.userSettingsFile, settings);
      return { success: true, settings };
    } catch (err) {
      return { success: false, error: err?.message || String(err) };
    }
  },
  fetchJson,

  // Symphony File Commands
  getSymphonyFiles: async (directoryPath) => {
    try {
      const entries = await Neutralino.filesystem.readDirectory(directoryPath);
      return entries
        .filter((e) => e.type === "FILE")
        .map((e) => e.entry)
        .filter((name) => VALID_FILE_EXTS.has(path.extname(name).toLowerCase()));
    } catch {
      return "not a valid dir";
    }
  },
  openNativeApp: async (filePath) => {
    try {
      await Neutralino.os.open(filePath);
      try {
        await addRecentlyViewed(filePath);
      } catch (err) {
        return { success: false, error: err?.message || String(err) };
      }
      return { success: true };
    } catch (err) {
      return { success: false, error: err?.message || String(err) };
    }
  },

  // Editor Program
  doProcessCommand: async (symphonyFilePath, command, extraArgs = {}) => {
    if (command === "open" && symphonyFilePath) {
      try {
        await addRecentlyViewed(symphonyFilePath);
      } catch (err) {
        console.error("Failed to add to recently viewed on open:", err);
      }
    }
    return doProcessCommand(symphonyFilePath, command, extraArgs);
  },
};

export { readBinaryAsArrayBuffer };
