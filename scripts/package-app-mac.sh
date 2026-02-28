#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
echo "[Symphony] Packaging macOS app from $(pwd)"

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
elif [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

PY_CMD="python3"
if [[ -x "venv/bin/python3" ]]; then
  PY_CMD="venv/bin/python3"
elif [[ -x ".venv/bin/python3" ]]; then
  PY_CMD=".venv/bin/python3"
elif [[ -x "venv/bin/python" ]]; then
  PY_CMD="venv/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PY_CMD=".venv/bin/python"
fi

echo "[1/4] Building inner app with PyInstaller..."
"$PY_CMD" -m PyInstaller --onefile --distpath ./inner/dist ./inner/src/main.py

echo "[2/4] Syncing inner assets..."
rm -rf ./inner/dist/assets
cp -R ./inner/src/assets ./inner/dist/assets

echo "[3/4] Building React app..."
npm run build:react

echo "[4/4] Building Electron macOS package..."
npm run build:electron -- --mac

echo "[Done] macOS package build complete."
