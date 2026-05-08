@echo off
setlocal

cd /d "%~dp0\.."
if errorlevel 1 (
  echo [Error] Failed to change to project root.
  exit /b 1
)
echo [Symphony] Packaging Windows app from %CD%

if not exist ".\inner\src\assets" (
  echo [Error] Missing source assets folder: .\inner\src\assets
  exit /b 1
)

echo [Symphony] Stopping any running Symphony / inner processes that could lock build outputs...
taskkill /F /IM "Symphony.exe" >nul 2>nul
taskkill /F /IM "main.exe" >nul 2>nul
rem Give the OS a moment to release file handles (e.g. app.asar)
ping -n 2 127.0.0.1 >nul

echo [0/5] Ensuring Python virtual environment exists...
if exist ".venv\Scripts\python.exe" (
  set "VENV_DIR=.venv"
) else if exist "venv\Scripts\python.exe" (
  set "VENV_DIR=venv"
) else (
  echo [Symphony] No venv found. Creating venv at .\venv ...
  where python >nul 2>nul
  if errorlevel 1 (
    echo [Error] Python is not on PATH. Install Python 3 and re-run.
    exit /b 1
  )
  python -m venv venv
  if errorlevel 1 goto :fail
  set "VENV_DIR=venv"
)

call "%VENV_DIR%\Scripts\Activate.bat"
if errorlevel 1 goto :fail

set "PY_CMD=%VENV_DIR%\Scripts\python.exe"

echo [1/5] Installing Python dependencies...
%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 goto :fail
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail
echo [Symphony] Installing packages that fail in requirements.txt...
%PY_CMD% -m pip install dill
if errorlevel 1 goto :fail
%PY_CMD% -m pip install music21
if errorlevel 1 goto :fail
%PY_CMD% -m pip install soundfile
if errorlevel 1 goto :fail
%PY_CMD% -m pip install pretty_midi
if errorlevel 1 goto :fail

echo [2/5] Building inner app with PyInstaller...
rem ----------------------------------------------------------------------------
rem PyInstaller exclusions. Each exclude has a specific reason; do NOT add to
rem this list without checking that the package is genuinely unreferenced at
rem runtime. See `scripts/packages_sorted.md` for size impact.
rem
rem matplotlib + private deps (contourpy/cycler/kiwisolver/fonttools/mpl_toolkits)
rem   transitive deps of music21/pretty_midi; Symphony never plots anything.
rem
rem chardet / joblib / jsonpickle
rem   referenced by music21 only inside lazy in-function imports
rem   (common/fileTools.py, common/parallel.py, freezeThaw.py). We never read
rem   text files via music21, never use music21 parallel utils, and never use
rem   music21's freeze/thaw (we serialize with dill directly).
rem
rem pip / _distutils_hack
rem   install-time tooling; never imported by Symphony at runtime.
rem   NOTE: setuptools, pkg_resources, and wheel are intentionally NOT excluded.
rem   pretty_midi/instrument.py:11 has an eager `import pkg_resources`, and
rem   pkg_resources itself imports `jaraco.text` and `platformdirs` from
rem   setuptools/_vendor/ via a runtime sys.path hack. So we must keep both.
rem   Note: setuptools is pinned `<82` in requirements.txt because setuptools
rem   82.0.0 (Feb 2026) removed the `pkg_resources` module entirely. altgraph
rem   (a PyInstaller dep) and pretty_midi both `import pkg_resources` eagerly,
rem   so newer setuptools breaks the build before PyInstaller even starts.
rem   pkg_resources is also added as a hidden import below to make the
rem   dependency explicit for future readers. `wheel` looks like install-time
rem   tooling, but in setuptools >= 71 it is a vendored package exposed via
rem   setuptools/_vendor/wheel/. Excluding it makes PyInstaller's setuptools
rem   hook fail when it tries to alias `wheel` -> `setuptools._vendor.wheel`
rem   (ValueError: Target module "wheel" already imported as ExcludedModule).
rem   It is not its own package on disk anyway, so excluding saves no bytes.
rem
rem PyInstaller / _pyinstaller_hooks_contrib / altgraph / pefile
rem   build-time tooling; never imported at runtime. (Bundled runtime hooks
rem   are baked into the bootloader, not loaded from these packages.)
rem
rem pythonwin / adodbapi / isapi / win32com / win32comext
rem   pywin32 extras for the Windows IDE / COM / IIS / database access.
rem   We only use ctypes.windll, never any pywin32 module.
rem
rem tkinter
rem   the only tkinter user is console_controls/console_window.py, whose import
rem   in main.py is commented out. Re-include if that import is ever revived.
rem ----------------------------------------------------------------------------
%PY_CMD% -m PyInstaller --clean --onefile --windowed ^
  --hidden-import music21 ^
  --hidden-import pkg_resources ^
  --exclude-module matplotlib ^
  --exclude-module mpl_toolkits ^
  --exclude-module contourpy ^
  --exclude-module cycler ^
  --exclude-module kiwisolver ^
  --exclude-module fonttools ^
  --exclude-module chardet ^
  --exclude-module joblib ^
  --exclude-module jsonpickle ^
  --exclude-module pip ^
  --exclude-module _distutils_hack ^
  --exclude-module PyInstaller ^
  --exclude-module _pyinstaller_hooks_contrib ^
  --exclude-module altgraph ^
  --exclude-module pefile ^
  --exclude-module pythonwin ^
  --exclude-module adodbapi ^
  --exclude-module isapi ^
  --exclude-module win32com ^
  --exclude-module win32comext ^
  --exclude-module tkinter ^
  --distpath ./inner/dist ./inner/src/main.py
if errorlevel 1 goto :fail

echo [3/5] Syncing inner assets...
if exist ".\inner\dist\assets" (
  rmdir /s /q ".\inner\dist\assets"
  if errorlevel 1 goto :fail
)
xcopy ".\inner\src\assets" ".\inner\dist\assets\" /e /i /y
if errorlevel 4 goto :fail

echo [4/5] Building React app...
call npm run build:react
if errorlevel 1 goto :fail

echo [5/5] Building Electron Windows package...
call npm run build:electron -- --win
if errorlevel 1 goto :fail

echo [Done] Windows package build complete.
exit /b 0

:fail
echo [Error] Build stopped due to a failure.
exit /b 1
