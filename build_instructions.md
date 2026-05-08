# Symphony Build Instructions

## Run Automatic Build

The new dev build architecture has the following scripts can run:

```bash
npm run package-app:windows
# or
npm run package-app:mac
```

These will run the needed scripts to place the app into build-ready mode.
Each script will:

1. Create a Python virtual environment at `./venv` if one is not already present (it
   also accepts an existing `./.venv`).
2. Activate the venv and `pip install -r requirements.txt`.
3. Install the packages that frequently fail to install via `requirements.txt`:
   `dill`, `music21`, `soundfile`, and `pretty_midi`.
4. Build the inner Python executable with PyInstaller, sync inner assets, build the
   React app, and run Electron Builder for the target platform.

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
            "inner/dist/assets/*.wav",
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
            "inner/dist/assets/*.wav",
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

1. Create (if needed) and activate the Python virtual environment:

```powershell
if (!(Test-Path .\venv\Scripts\python.exe)) { python -m venv venv }
.\venv\Scripts\Activate.ps1
```

1. Install Python dependencies (including the packages that often fail to install
   from `requirements.txt` alone):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install dill
python -m pip install music21
python -m pip install soundfile
python -m pip install pretty_midi
```

1. Build the inner executable:

```powershell
python -m PyInstaller --clean --onefile --windowed `
  --hidden-import music21 `
  --hidden-import pkg_resources `
  --exclude-module matplotlib `
  --exclude-module mpl_toolkits `
  --exclude-module contourpy `
  --exclude-module cycler `
  --exclude-module kiwisolver `
  --exclude-module fonttools `
  --exclude-module chardet `
  --exclude-module joblib `
  --exclude-module jsonpickle `
  --exclude-module pip `
  --exclude-module _distutils_hack `
  --exclude-module PyInstaller `
  --exclude-module _pyinstaller_hooks_contrib `
  --exclude-module altgraph `
  --exclude-module pefile `
  --exclude-module pythonwin `
  --exclude-module adodbapi `
  --exclude-module isapi `
  --exclude-module win32com `
  --exclude-module win32comext `
  --exclude-module tkinter `
  --distpath ./inner/dist ./inner/src/main.py
```

> The `--exclude-module` flags drop ~65 MB of dead weight that PyInstaller would
> otherwise sweep into the bundle. The exclusion categories are:
>
> 1. **matplotlib + private deps** (`matplotlib`, `mpl_toolkits`, `contourpy`,
>    `cycler`, `kiwisolver`, `fonttools`) — transitive deps of `music21` /
>    `pretty_midi`; Symphony never plots anything.
> 2. **music21 lazy deps** (`chardet`, `joblib`, `jsonpickle`) — referenced only
>    inside lazy in-function imports for code paths we never trigger.
> 3. **install-time tooling** (`pip`, `_distutils_hack`) — never imported at
>    runtime. `wheel` deliberately stays in (see the note below).
> 4. **build-time tooling** (`PyInstaller`, `_pyinstaller_hooks_contrib`,
>    `altgraph`, `pefile`) — runtime hooks are baked into the bootloader, not
>    loaded from these packages.
> 5. **pywin32 extras** (`pythonwin`, `adodbapi`, `isapi`, `win32com`,
>    `win32comext`) — Windows IDE / COM / IIS / database access; we only use
>    `ctypes.windll`.
> 6. **tkinter** — the only tkinter user is `console_controls/console_window.py`,
>    whose import in `main.py` is commented out. Re-include if that import is
>    ever revived.
>
> **NOTE:** `setuptools`, `pkg_resources`, and `wheel` are intentionally NOT
> excluded. `pretty_midi/instrument.py:11` has an eager `import pkg_resources`,
> and `pkg_resources` itself imports `jaraco.text` and `platformdirs` from
> `setuptools/_vendor/` via a runtime `sys.path` hack. `pkg_resources` is also
> listed as a `--hidden-import` to make the dependency explicit.
>
> `wheel` looks like install-time tooling, but with `setuptools >= 71` it is a
> vendored package exposed via `setuptools/_vendor/wheel/`. Excluding it causes
> PyInstaller's setuptools hook to fail when it tries to alias `wheel` →
> `setuptools._vendor.wheel` (`ValueError: Target module "wheel" already
> imported as ExcludedModule`). It is not its own package on disk anyway, so
> the exclusion would not save any bytes.
>
> Keep this list in sync with `scripts/package-app-windows.bat`,
> `scripts/package-app-mac.sh`, and `main.spec`.

1. Sync inner runtime assets:

```powershell
if (!(Test-Path .\inner\src\assets)) { throw "Missing .\inner\src\assets" }
if (Test-Path .\inner\dist\assets) { Remove-Item -Recurse -Force .\inner\dist\assets }
Copy-Item -Recurse .\inner\src\assets .\inner\dist\assets
```

1. Build React and Electron:

```powershell
npm run build:react
npm run build:electron -- --win
```

The Windows installer output is produced by Electron Builder in the default output folder (typically `dist/`).

## macOS Build

Run all commands from the project root.

1. Create (if needed) and activate the Python virtual environment:

```bash
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
```

1. Install Python dependencies (including the packages that often fail to install
   from `requirements.txt` alone):

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install dill
python3 -m pip install music21
python3 -m pip install soundfile
python3 -m pip install pretty_midi
```

1. Build the inner executable:

```bash
python3 -m PyInstaller --clean --onefile \
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
```

> See the Windows section above for the full reasoning behind each exclusion
> group. (Windows-only packages — `pefile`, `pythonwin`, `adodbapi`, `isapi`,
> `win32com`, `win32comext` — are omitted here since they aren't installed on
> macOS in the first place.)

1. Sync inner runtime assets:

```bash
set -euo pipefail
test -d ./inner/src/assets || { echo "Missing ./inner/src/assets"; exit 1; }
if [ -d ./inner/dist/assets ]; then rm -rf ./inner/dist/assets; fi
cp -R ./inner/src/assets ./inner/dist/assets
```

1. Build React and Electron:

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

