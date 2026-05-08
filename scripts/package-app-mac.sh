#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
echo "[Symphony] Packaging macOS app from $(pwd)"

if [[ ! -d "./inner/src/assets" ]]; then
  echo "[Error] Missing source assets folder: ./inner/src/assets"
  exit 1
fi

echo "[0/6] Ensuring Python virtual environment exists..."
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

echo "[1/6] Installing Python dependencies..."
"$PY_CMD" -m pip install --upgrade pip
"$PY_CMD" -m pip install -r requirements.txt
echo "[Symphony] Installing packages that fail in requirements.txt..."
"$PY_CMD" -m pip install dill
"$PY_CMD" -m pip install music21
"$PY_CMD" -m pip install soundfile
"$PY_CMD" -m pip install pretty_midi

echo "[2/6] Building inner app with PyInstaller..."
# -----------------------------------------------------------------------------
# PyInstaller exclusions. Each exclude has a specific reason; do NOT add to
# this list without checking that the package is genuinely unreferenced at
# runtime. See `scripts/packages_sorted.md` for size impact.
#
# matplotlib + private deps (contourpy/cycler/kiwisolver/fonttools/mpl_toolkits)
#   transitive deps of music21/pretty_midi; Symphony never plots anything.
#
# chardet / joblib / jsonpickle
#   referenced by music21 only inside lazy in-function imports
#   (common/fileTools.py, common/parallel.py, freezeThaw.py). We never read
#   text files via music21, never use music21 parallel utils, and never use
#   music21's freeze/thaw (we serialize with dill directly).
#
# pip / _distutils_hack
#   install-time tooling; never imported by Symphony at runtime.
#   NOTE: setuptools, pkg_resources, and wheel are intentionally NOT excluded.
#   pretty_midi/instrument.py:11 has an eager `import pkg_resources`, and
#   pkg_resources itself imports `jaraco.text` and `platformdirs` from
#   setuptools/_vendor/ via a runtime sys.path hack. So we must keep both.
#   pkg_resources is also added as a hidden import below to make the
#   dependency explicit for future readers. `wheel` looks like install-time
#   tooling, but in setuptools >= 71 it is a vendored package exposed via
#   setuptools/_vendor/wheel/. Excluding it makes PyInstaller's setuptools
#   hook fail when it tries to alias `wheel` -> `setuptools._vendor.wheel`
#   (ValueError: Target module "wheel" already imported as ExcludedModule).
#   It is not its own package on disk anyway, so excluding saves no bytes.
#
# PyInstaller / _pyinstaller_hooks_contrib / altgraph
#   build-time tooling; never imported at runtime. (Bundled runtime hooks
#   are baked into the bootloader, not loaded from these packages.)
#
# tkinter
#   the only tkinter user is console_controls/console_window.py, whose import
#   in main.py is commented out. Re-include if that import is ever revived.
# -----------------------------------------------------------------------------
"$PY_CMD" -m PyInstaller --clean --onefile \
  --hidden-import music21 \
  --hidden-import pkg_resources \
  --exclude-module matplotlib \
  --exclude-module mpl_toolkits \
  --exclude-module contourpy \
  --exclude-module cycler \
  --exclude-module kiwisolver \
  --exclude-module fonttools \
  --exclude-module chardet \
  --exclude-module joblib \
  --exclude-module jsonpickle \
  --exclude-module pip \
  --exclude-module _distutils_hack \
  --exclude-module PyInstaller \
  --exclude-module _pyinstaller_hooks_contrib \
  --exclude-module altgraph \
  --exclude-module tkinter \
  --distpath ./inner/dist ./inner/src/main.py

echo "[3/6] Syncing inner assets..."
rm -rf ./inner/dist/assets
cp -R ./inner/src/assets ./inner/dist/assets

echo "[4/6] Building React app..."
npm run build:react

echo "[5/6] Updating Neutralino framework binaries..."
npx --yes @neutralinojs/neu update

echo "[6/6] Building Neutralino macOS package..."
npx --yes @neutralinojs/neu build --release

echo "[Done] macOS package build complete. Output under ./dist-neu/"
