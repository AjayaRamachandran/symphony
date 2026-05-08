// Editor process management. The Python editor (PyInstaller-built `main.exe`
// or `main.py` in dev) is launched as a long-running background process that
// the renderer talks to by writing JSON commands to `process-command.json`
// inside the user's data directory and polling for a status response.
//
// This module replaces the equivalent logic in the old Electron `main.js`.

import * as Neutralino from "@neutralinojs/lib";
import path from "path-browserify";

let persistEditor = true;
let activeProcessCommandPath = null;

const POLL_INTERVAL_MS = 100;
const POLL_TIMEOUT_MS = 15000;

function uuid() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function pathExists(p) {
  try {
    await Neutralino.filesystem.getStats(p);
    return true;
  } catch {
    return false;
  }
}

async function safeReadJson(filePath) {
  try {
    const text = await Neutralino.filesystem.readFile(filePath);
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function writeJson(filePath, value) {
  await Neutralino.filesystem.writeFile(filePath, JSON.stringify(value, null, 2));
}

function sleep(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

function quote(s) {
  if (s == null) return "";
  return `"${String(s).replace(/"/g, '\\"')}"`;
}

function buildSpawnCommand({ executablePath, isPythonScript, sourcePath, commandPath, platform }) {
  const exe = executablePath;
  const args = [sourcePath, commandPath];

  if (isPythonScript) {
    const py = platform === "win32" ? "pythonw" : "python3";
    return `${py} -u ${quote(exe)} ${args.map(quote).join(" ")}`;
  }
  return `${quote(exe)} ${args.map(quote).join(" ")}`;
}

async function spawnAndKeepAlive(opts) {
  const command = buildSpawnCommand(opts);
  const proc = await Neutralino.os.spawnProcess(command);
  let exited = false;

  const onSpawn = (evt) => {
    if (!evt?.detail || evt.detail.id !== proc.id) return;
    const action = evt.detail.action;
    if (action === "stdOut") {
      try {
        console.log("[editor]", evt.detail.data);
      } catch {}
    } else if (action === "stdErr") {
      try {
        console.error("[editor]", evt.detail.data);
      } catch {}
    } else if (action === "exit") {
      if (exited) return;
      exited = true;
      Neutralino.events.off("spawnedProcess", onSpawn);
      const code = evt.detail.data;
      if (code !== 0) {
        console.error(`Editor process crashed with code ${code}.`);
      } else {
        console.log("Editor process exited.");
      }
      if (persistEditor) {
        console.log("Restarting editor...");
        spawnAndKeepAlive(opts).catch((err) => {
          console.error("Failed to respawn editor:", err);
        });
      } else {
        console.log("Editor stop allowed.");
      }
    }
  };

  Neutralino.events.on("spawnedProcess", onSpawn);
  return proc;
}

export async function startEditor(opts) {
  const { processCommandPath, executablePath, isPythonScript, innerDistPath, platform } = opts;
  activeProcessCommandPath = processCommandPath;
  persistEditor = true;

  try {
    await writeJson(processCommandPath, { command: "kill" });
    await sleep(500);
    await writeJson(processCommandPath, {});

    if (!(await pathExists(executablePath))) {
      console.warn(
        `[symphony] Editor executable not found at ${executablePath}. Skipping editor spawn.`,
      );
      return { success: false, error: "Editor executable not found" };
    }

    await spawnAndKeepAlive({
      executablePath,
      isPythonScript,
      sourcePath: innerDistPath,
      commandPath: processCommandPath,
      platform,
    });
    return { success: true, message: "Editor daemon started" };
  } catch (err) {
    console.error("Failed to start editor:", err);
    return { success: false, error: err?.message || String(err) };
  }
}

export async function stopEditor() {
  persistEditor = false;
  try {
    await doProcessCommand("", "kill", {});
  } catch (err) {
    console.error("stopEditor failed:", err);
  }
}

export async function doProcessCommand(symphonyFilePath, command, extraArgs = {}) {
  if (!activeProcessCommandPath) {
    return { success: false, error: "Editor process not initialised" };
  }

  const id = uuid();
  const projectFolderPath = path.dirname(symphonyFilePath || "");
  const projectFileName = path.basename(symphonyFilePath || "", ".symphony");
  const dataDir = path.dirname(activeProcessCommandPath);

  const processCommand = {
    command,
    id,
    pc_file_path: activeProcessCommandPath,
    args: {
      project_file_name: projectFileName,
      project_folder_path: projectFolderPath,
      symphony_data_path: dataDir,
      ...extraArgs,
    },
  };

  await writeJson(activeProcessCommandPath, processCommand);
  await sleep(1000);

  let waited = 0;
  while (waited < POLL_TIMEOUT_MS) {
    const data = await safeReadJson(activeProcessCommandPath);
    if (data && data.id === id && data.status) {
      return data;
    }
    await sleep(POLL_INTERVAL_MS);
    waited += POLL_INTERVAL_MS;
  }

  const last = await safeReadJson(activeProcessCommandPath);
  return last || { timeout: true };
}
