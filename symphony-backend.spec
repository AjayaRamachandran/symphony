# PyInstaller spec for the Symphony pywebview backend.
#
# Produces ``dist/symphony-backend(.exe)`` which the Tauri launcher invokes as
# a sidecar. The build script (npm run build:backend) copies it into
# ``src-tauri/binaries/`` with the platform triple suffix Tauri expects.
#
# This file is intentionally written for PyInstaller 6.x: it does NOT use
# the legacy ``cipher`` / ``block_cipher`` arguments, ``a.zipfiles`` (gone
# since PyInstaller 5), or the ``win_no_prefer_redirects`` /
# ``win_private_assemblies`` flags (gone since PyInstaller 6). Those silently
# degrade the data collection in newer PyInstaller, producing a tiny ~13 MB
# bundle missing dist/, inner/dist/, and src/assets/.

# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SPEC_DIR = Path(os.path.abspath(SPECPATH))  # noqa: F821 (PyInstaller-injected)


def _require_dir(rel: str) -> str:
    p = SPEC_DIR / rel
    if not p.exists():
        raise SystemExit(
            f"[symphony-backend.spec] required data path missing: {p}. "
            "Build the React app (npm run build:react) and the inner editor "
            "(PyInstaller on inner/src/main.py) before building the backend."
        )
    return str(p)


_require_dir("dist")
_require_dir("inner/dist")
_require_dir("src/assets")

# pywebview ships JS / native shims that must travel with the binary.
webview_datas = collect_data_files("webview")
webview_hidden = collect_submodules("webview")

datas = [
    ("config.yaml", "."),
    ("dist", "dist"),
    ("inner/dist", "inner/dist"),
    ("src/assets", "src/assets"),
    *webview_datas,
]

hiddenimports = [
    *webview_hidden,
    "platformdirs",
    "yaml",
]

icon_path = SPEC_DIR / "src-tauri" / "icons" / ("icon.ico" if sys.platform == "win32" else "icon.icns")
icon = str(icon_path) if icon_path.exists() else None

a = Analysis(
    ["main.py"],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="symphony-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=True is intentional: the Tauri launcher reads stdout/stderr
    # for the __SYMPHONY_READY__ marker that hides the splash window.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
