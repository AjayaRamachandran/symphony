# PyInstaller spec for the Symphony pywebview backend.
#
# Produces ``dist/symphony-backend(.exe)`` which the Tauri launcher invokes as
# a sidecar. The build script (npm run build:backend) copies it into
# ``src-tauri/binaries/`` with the platform triple suffix Tauri expects.

# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# pywebview loads its JS payload at runtime — collect_data_files pulls those in.
webview_datas = collect_data_files("webview")

datas = [
    ("config.yaml", "."),
    ("dist", "dist"),
    ("inner/dist", "inner/dist"),
    ("src/assets", "src/assets"),
    *webview_datas,
]

hiddenimports = [
    *collect_submodules("webview"),
    "platformdirs",
    "yaml",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="symphony-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=True is intentional: the Tauri launcher reads stdout/stderr.
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="build/icon.ico" if sys.platform == "win32" else None,
)
