#!/usr/bin/env python3
"""Patch webview's edgechromium.py to enable IsNonClientRegionSupportEnabled.

Safe to run multiple times — no-op if the patch is already present.
Works on Windows and macOS (anywhere Python 3 is available).

Usage:
    python patch-webview.py          # auto-detects the right file
    python patch-webview.py --check  # exit 0 if patched, 1 if not (no changes)
"""

import sys
import textwrap
from pathlib import Path

ANCHOR = "settings.IsZoomControlEnabled = True"

PATCH_BLOCK = textwrap.dedent("""\
        try:
            settings.IsNonClientRegionSupportEnabled = True
        except AttributeError:
            pass  # WebView2 SDK < 1.0.2357 does not expose this property
""")

ALREADY_PATCHED_MARKER = "IsNonClientRegionSupportEnabled"


def find_target() -> Path:
    base = Path(__file__).resolve().parent
    for venv_name in ("venv", ".venv", "env"):
        hits = list((base / venv_name).glob("**/webview/platforms/edgechromium.py"))
        if hits:
            return hits[0]
    # Fall back to whatever Python resolves at runtime
    try:
        import webview.platforms.edgechromium as _ec
        return Path(_ec.__file__)
    except ImportError:
        pass
    raise FileNotFoundError(
        "Could not locate webview/platforms/edgechromium.py. "
        "Make sure the virtual environment is active or the path is resolvable."
    )


def main() -> int:
    check_only = "--check" in sys.argv

    try:
        target = find_target()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    content = target.read_text(encoding="utf-8")

    if ALREADY_PATCHED_MARKER in content:
        print(f"Already patched: {target}")
        return 0

    if check_only:
        print(f"NOT patched: {target}")
        return 1

    if ANCHOR not in content:
        print(
            f"ERROR: anchor line not found in {target}\n"
            f"  Expected: {ANCHOR!r}\n"
            "The pywebview version may have changed — inspect the file manually.",
            file=sys.stderr,
        )
        return 1

    patched = content.replace(ANCHOR, ANCHOR + "\n" + PATCH_BLOCK, 1)
    target.write_text(patched, encoding="utf-8")
    print(f"Patched: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
