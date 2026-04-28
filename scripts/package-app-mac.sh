#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
echo "[Symphony] Packaging macOS app from $(pwd)"

if [[ ! -d "./inner/src/assets" ]]; then
  echo "[Error] Missing source assets folder: ./inner/src/assets"
  exit 1
fi

echo "[0/5] Ensuring Python virtual environment exists..."
if [[ -d ".venv" ]]; then
  VENV_DIR=".venv"
elif [[ -d "venv" ]]; then
  VENV_DIR="venv"
else
  echo "[Symphony] No venv found. Creating venv at ./venv ..."
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv venv
  elif command -v python >/dev/null 2>&1; then
    python -m venv venv
  else
    echo "[Error] Python is not on PATH. Install Python 3 and re-run."
    exit 1
  fi
  VENV_DIR="venv"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [[ -x "$VENV_DIR/bin/python3" ]]; then
  PY_CMD="$VENV_DIR/bin/python3"
elif [[ -x "$VENV_DIR/bin/python" ]]; then
  PY_CMD="$VENV_DIR/bin/python"
else
  PY_CMD="python3"
fi

echo "[1/5] Installing Python dependencies..."
"$PY_CMD" -m pip install --upgrade pip
"$PY_CMD" -m pip install -r requirements.txt
echo "[Symphony] Installing packages that fail in requirements.txt..."
"$PY_CMD" -m pip install dill
"$PY_CMD" -m pip install music21
"$PY_CMD" -m pip install soundfile
"$PY_CMD" -m pip install pretty_midi

echo "[2/5] Building inner app with PyInstaller..."
"$PY_CMD" -m PyInstaller --clean --onefile --hidden-import music21 --distpath ./inner/dist ./inner/src/main.py

echo "[3/5] Syncing inner assets..."
rm -rf ./inner/dist/assets
cp -R ./inner/src/assets ./inner/dist/assets

echo "[4/5] Building React app..."
npm run build:react

echo "[5/5] Building Electron macOS package..."
npm run build:electron -- --mac

echo "[Done] macOS package build complete."
