# Symphony Build Instructions

## Run Automatic Build
The new dev build architecture has the following scripts can run:
```bash
npm run package-app:windows
# or
npm run package-app:mac
```
These will run the needed scripts to place the app into build-ready mode.
If there is a build-time error, then follow the below instructions.

## Run Manual Build

Use this `package.json` content before starting a build:

```json
{
    "name": "symphony",
    "private": true,
    "version": "0.0.0",
    "main": "main.js",
    "forceCodeSigning": false,
    "build": {
        "appId": "com.ajayarsymphony.app",
        "productName": "Symphony",
        "asarUnpack": [
            "inner/dist/main.exe",
            "inner/dist/main",
            "inner/dist/workingfile.symphony",
            "inner/dist/assets/*.png",
            "inner/dist/assets/*.ttf"
        ],
        "files": [
            "dist/",
            "main.js",
            "preload.js",
            "index.html",
            "inner/dist/main.exe",
            "inner/dist/main",
            "inner/dist/assets/*.png",
            "inner/dist/assets/*.ttf",
            "src/assets/*.json",
            "src/assets/*.png",
            "src/assets/*.svg",
            "build/"
        ],
        "win": {
            "icon": "build/icon.ico",
            "target": "nsis",
            "signAndEditExecutable": true
        },
        "mac": {
            "icon": "build/icon.icns",
            "target": [
                "dmg",
                "zip"
            ],
            "category": "public.app-category.music",
            "hardenedRuntime": true
        }
    },
    "scripts": {
        "build:react": "vite build",
        "build:electron": "electron-builder",
        "package-app:windows": ".\\scripts\\package-app-windows.bat",
        "package-app:mac": "sh ./scripts/package-app-mac.sh",
        "lint": "eslint",
        "preview": "vite preview",
        "start": "vite",
        "electron": "electron ./main.js",
        "dev": "concurrently -k \"vite\" \"electron ./main.js\"",
        "vite": "vite"
    }
}
```

## Windows Build

Run all commands from the project root.

1) Activate the Python virtual environment:

```powershell
venv\Scripts\Activate
```

2) Build the inner executable:

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --clean --onefile --windowed --hidden-import music21 --distpath ./inner/dist ./inner/src/main.py
```

3) Sync inner runtime assets:

```powershell
if (!(Test-Path .\inner\src\assets)) { throw "Missing .\inner\src\assets" }
if (Test-Path .\inner\dist\assets) { Remove-Item -Recurse -Force .\inner\dist\assets }
Copy-Item -Recurse .\inner\src\assets .\inner\dist\assets
```

4) Build React and Electron:

```powershell
npm run build:react
npm run build:electron -- --win
```

The Windows installer output is produced by Electron Builder in the default output folder (typically `dist/`).

## macOS Build

Run all commands from the project root.

1) Activate the Python virtual environment:

```bash
source venv/bin/activate
```

2) Build the inner executable:

```bash
python3 -m PyInstaller --onefile --distpath ./inner/dist ./inner/src/main.py
```

3) Sync inner runtime assets:

```bash
set -euo pipefail
test -d ./inner/src/assets || { echo "Missing ./inner/src/assets"; exit 1; }
if [ -d ./inner/dist/assets ]; then rm -rf ./inner/dist/assets; fi
cp -R ./inner/src/assets ./inner/dist/assets
```

4) Build React and Electron:

```bash
npm run build:react
npm run build:electron -- --mac
```

## Optional Quick Verification

Before packaging, verify these files exist:

- `inner/dist/main.exe` (Windows) or `inner/dist/main` (macOS)
- `inner/dist/assets/InterVariable.ttf`
- `inner/dist/assets/play.png` (and other runtime PNG assets)
- `build/icon.ico` and/or `build/icon.icns`

## Icon Troubleshooting (Windows)

If the built app uses the wrong icon, run PowerShell as Administrator in the project folder:

```powershell
Remove-Item -Recurse -Force "C:\Users\Ajaya\AppData\Local\electron-builder\Cache\winCodeSign"
$env:CSC_IDENTITY_AUTO_DISCOVERY="false"
$env:CSC_IDENTITY=""
npm run build:electron -- --win
```

