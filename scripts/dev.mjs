import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const TEST_IMPORT_FLAG = "--test-import";

function readTestImportArg(args) {
  const passthrough = [];
  let testImportPath = null;

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === TEST_IMPORT_FLAG) {
      testImportPath = args[i + 1] || null;
      i += 1;
      continue;
    }
    if (arg.startsWith(`${TEST_IMPORT_FLAG}=`)) {
      testImportPath = arg.slice(TEST_IMPORT_FLAG.length + 1);
      continue;
    }
    passthrough.push(arg);
  }

  return { testImportPath, passthrough };
}

let { testImportPath, passthrough } = readTestImportArg(process.argv.slice(2));
const npmConfigTestImport = process.env.npm_config_test_import;
if (
  !testImportPath &&
  npmConfigTestImport &&
  npmConfigTestImport !== "false"
) {
  if (npmConfigTestImport !== "true") {
    testImportPath = npmConfigTestImport;
  } else if (passthrough.length > 0) {
    [testImportPath, ...passthrough] = passthrough;
  }
}
const env = { ...process.env };
const invocationCwd = process.env.INIT_CWD || process.cwd();

if (
  npmConfigTestImport &&
  npmConfigTestImport !== "false" &&
  !testImportPath
) {
  console.error(`${TEST_IMPORT_FLAG} requires a .symphony file path.`);
  process.exit(1);
}

if (testImportPath) {
  const resolvedPath = resolve(invocationCwd, testImportPath);
  if (!resolvedPath.toLowerCase().endsWith(".symphony")) {
    console.error(`${TEST_IMPORT_FLAG} expects a .symphony file path.`);
    process.exit(1);
  }
  if (!existsSync(resolvedPath)) {
    console.warn(
      `${TEST_IMPORT_FLAG}: ${resolvedPath} does not exist; showing the import UI with a mock path.`,
    );
  }
  env.SYMPHONY_TEST_IMPORT = resolvedPath;
  env.SYMPHONY_OPEN_FILE = resolvedPath;
}

const child = spawn("tauri", ["dev", ...passthrough], {
  cwd: process.cwd(),
  env,
  stdio: "inherit",
  shell: true,
});

child.on("exit", (code, signal) => {
  if (signal) {
    console.error(`tauri dev exited with signal ${signal}`);
    process.exit(1);
  }
  process.exit(code ?? 1);
});
