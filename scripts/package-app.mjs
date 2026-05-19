// Cross-platform dispatcher for `npm run package-app`.
// Picks the OS-specific script and execs it, inheriting stdio.

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function run(cmd, args) {
  return new Promise((res, rej) => {
    const child = spawn(cmd, args, { stdio: "inherit", cwd: root, shell: true });
    child.on("exit", (code) => (code === 0 ? res() : rej(new Error(`${cmd} exited ${code}`))));
  });
}

const platform = process.platform;
let script;
if (platform === "win32") {
  script = resolve(root, "scripts", "package-app-windows.bat");
} else if (platform === "darwin") {
  script = resolve(root, "scripts", "package-app-mac.sh");
} else {
  console.error(`Unsupported platform: ${platform}`);
  process.exit(1);
}

if (!existsSync(script)) {
  console.error(`Missing build script: ${script}`);
  process.exit(1);
}

try {
  if (platform === "win32") {
    await run("cmd", ["/c", script]);
  } else {
    await run("bash", [script]);
  }
} catch (err) {
  console.error(err.message);
  process.exit(1);
}
