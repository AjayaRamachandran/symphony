// Copies the PyInstaller output (dist/symphony-backend[.exe]) into
// src-tauri/binaries/ with the rustc target-triple suffix Tauri expects for
// externalBin sidecars.

import { execSync } from "node:child_process";
import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

const projectRoot = resolve(new URL(".", import.meta.url).pathname, "..");
const isWin = process.platform === "win32";

function rustTargetTriple() {
  try {
    const out = execSync("rustc -vV", { encoding: "utf8" });
    const m = out.match(/host:\s*(\S+)/);
    if (m) return m[1];
  } catch (err) {
    console.error("rustc not found; cannot determine target triple.", err.message);
    process.exit(1);
  }
  console.error("Failed to parse rustc host triple.");
  process.exit(1);
}

const triple = rustTargetTriple();
const exeName = isWin ? "symphony-backend.exe" : "symphony-backend";
const src = join(projectRoot, "dist", exeName);
if (!existsSync(src)) {
  console.error(`Backend binary not found at ${src}. Run pyinstaller first.`);
  process.exit(1);
}

const targetDir = join(projectRoot, "src-tauri", "binaries");
mkdirSync(targetDir, { recursive: true });
const destName = isWin
  ? `symphony-backend-${triple}.exe`
  : `symphony-backend-${triple}`;
const dest = join(targetDir, destName);
copyFileSync(src, dest);
console.log(`Staged sidecar: ${dest}`);
