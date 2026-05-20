// Build only the installer bundle for the current platform.
// Windows produces an NSIS setup.exe; macOS produces a dmg.
//
// The sidecar (symphony-backend) and resources are declared in
// src-tauri/tauri.conf.json so a plain `tauri build` always includes them.

import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const bundleByPlatform = {
  win32: "nsis",
  darwin: "dmg",
};

const bundle = bundleByPlatform[process.platform];

if (!bundle) {
  console.error(`Unsupported platform for installer build: ${process.platform}`);
  process.exit(1);
}

const args = ["build", "--bundles", bundle];

const child = spawn("tauri", args, {
  cwd: root,
  stdio: "inherit",
  shell: true,
});

child.on("exit", (code) => process.exit(code ?? 1));
