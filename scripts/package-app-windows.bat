@echo off
setlocal

cd /d "%~dp0\.."
if errorlevel 1 (
  echo [Error] Failed to change to project root.
  exit /b 1
)
echo [Symphony] Packaging Windows app from %CD%

if exist "venv\Scripts\Activate.bat" (
  call "venv\Scripts\Activate.bat"
) else if exist ".venv\Scripts\Activate.bat" (
  call ".venv\Scripts\Activate.bat"
) else (
  echo [Error] No virtual environment activation script found at venv\Scripts\Activate.bat or .venv\Scripts\Activate.bat.
  exit /b 1
)
if errorlevel 1 goto :fail

if exist ".venv\Scripts\python.exe" (
  set "PY_CMD=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
  set "PY_CMD=venv\Scripts\python.exe"
) else (
  echo [Error] No venv Python executable found at venv\Scripts\python.exe or .venv\Scripts\python.exe.
  exit /b 1
)

if not exist ".\inner\src\assets" (
  echo [Error] Missing source assets folder: .\inner\src\assets
  exit /b 1
)

echo [0/4] Installing Python dependencies...
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [1/4] Building inner app with PyInstaller...
%PY_CMD% -m PyInstaller --clean --onefile --windowed --hidden-import music21 --distpath ./inner/dist ./inner/src/main.py
if errorlevel 1 goto :fail

echo [2/4] Syncing inner assets...
if exist ".\inner\dist\assets" (
  rmdir /s /q ".\inner\dist\assets"
  if errorlevel 1 goto :fail
)
xcopy ".\inner\src\assets" ".\inner\dist\assets\" /e /i /y
if errorlevel 4 goto :fail

echo [3/4] Building React app...
call npm run build:react
if errorlevel 1 goto :fail

echo [4/4] Building Electron Windows package...
call npm run build:electron -- --win
if errorlevel 1 goto :fail

echo [Done] Windows package build complete.
exit /b 0

:fail
echo [Error] Build stopped due to a failure.
exit /b 1
