// Pre-flight check for the Tauri installer build.
//
// Verifies that every artifact the Tauri bundler is about to pick up exists
// and reports its on-disk size. Fails (non-zero exit) if anything is missing
// or suspiciously small so we never ship a 15 MB "splash-only" installer.

import { execSync } from "node:child_process";
import { existsSync, statSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";

function rustTargetTriple() {
  try {
    const out = execSync("rustc -vV", { encoding: "utf8" });
    const m = out.match(/host:\s*(\S+)/);
    if (m) return m[1];
  } catch (err) {
    console.error("[verify] rustc not found; cannot determine target triple.", err.message);
    process.exit(1);
  }
  console.error("[verify] failed to parse rustc host triple.");
  process.exit(1);
}

function dirSize(path) {
  let total = 0;
  const stack = [path];
  while (stack.length) {
    const cur = stack.pop();
    let entries;
    try {
      entries = readdirSync(cur, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      const full = join(cur, ent.name);
      if (ent.isDirectory()) stack.push(full);
      else {
        try {
          total += statSync(full).size;
        } catch {
          // ignore unreadable entries
        }
      }
    }
  }
  return total;
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

const triple = rustTargetTriple();
const innerEditor = isWin ? "inner/dist/main.exe" : "inner/dist/main";
const backendExe = isWin ? "dist/symphony-backend.exe" : "dist/symphony-backend";
const stagedSidecar = isWin
  ? `src-tauri/binaries/symphony-backend-${triple}.exe`
  : `src-tauri/binaries/symphony-backend-${triple}`;

// Minimum sizes are conservative floors that catch a broken bundle without
// false-flagging a healthy one. The Symphony architecture nests one
// PyInstaller bundle (the inner editor) inside another (the backend sidecar),
// so the backend is typically ~60-80 MB on Windows / ~70-100 MB on macOS,
// not the 130-200 MB you'd see if everything were in a single layer.
const checks = [
  { label: "Inner editor (PyInstaller)", path: innerEditor, minMB: 20 },
  { label: "Inner editor assets", path: "inner/dist/assets", minMB: 1, dir: true },
  { label: "React app (Vite)", path: "dist/index.html", minMB: 0 },
  { label: "Symphony backend (PyInstaller)", path: backendExe, minMB: 40 },
  { label: "Staged Tauri sidecar", path: stagedSidecar, minMB: 40 },
];

let failed = false;
console.log("[verify] Pre-flight artifact check:");
for (const c of checks) {
  const full = join(root, c.path);
  if (!existsSync(full)) {
    console.error(`  MISSING  ${c.label}: ${c.path}`);
    failed = true;
    continue;
  }
  const size = c.dir ? dirSize(full) : statSync(full).size;
  const sizeMB = size / (1024 * 1024);
  const ok = sizeMB >= c.minMB;
  const tag = ok ? "OK " : "WARN";
  if (!ok) failed = true;
  console.log(`  ${tag}      ${c.label}: ${c.path} (${fmtSize(size)}, expected >= ${c.minMB} MB)`);
}

if (failed) {
  console.error(
    "\n[verify] One or more build artifacts are missing or smaller than expected. " +
      "Re-run the build steps before Tauri packaging. A correct Symphony backend " +
      "bundle is typically 60-100 MB because it ships the Python runtime, pywebview, " +
      "the React dist/, src/assets/, and the inner editor exe (which itself bundles " +
      "music21, numpy, soundfile, and pretty_midi)."
  );
  process.exit(1);
}

console.log("[verify] All artifacts present and meet minimum size expectations.");
