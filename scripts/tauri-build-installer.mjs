// Build only the installer bundle for the current platform.
// Windows produces an NSIS setup.exe; macOS produces a dmg.

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

const args = [
  "build",
  "-c",
  "src-tauri/tauri.bundle.conf.json",
  "--bundles",
  bundle,
];

const child = spawn("tauri", args, {
  cwd: root,
  stdio: "inherit",
  shell: true,
});

child.on("exit", (code) => process.exit(code ?? 1));
