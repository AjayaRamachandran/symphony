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
%PY_CMD% -m PyInstaller --clean --onefile --windowed --hidden-import music21 --distpath ./inner/dist ./inner/src/main.py
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
