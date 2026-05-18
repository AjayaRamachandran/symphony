"""Symphony pywebview backend.

Replaces the Electron main process (main.js). Renders the Vite frontend in a
pywebview window and exposes a ``js_api`` whose method names are consumed by
``src/electron-api-shim.js`` to provide ``window.electronAPI``.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.parse import urlparse

import webview
import yaml
from platformdirs import user_data_dir


APP_NAME = "Symphony"
IS_FROZEN = getattr(sys, "frozen", False)
APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

USER_DATA_PATH = Path(user_data_dir(APP_NAME, appauthor=False, roaming=True))
USER_DATA_PATH.mkdir(parents=True, exist_ok=True)
DIRECTORY_PATH = USER_DATA_PATH / "directory.json"
RECENTLY_VIEWED_PATH = USER_DATA_PATH / "recently-viewed.json"
STARRED_PATH = USER_DATA_PATH / "starred.json"
USER_SETTINGS_PATH = USER_DATA_PATH / "user-settings.json"
PROCESS_COMMAND_PATH = USER_DATA_PATH / "process-command.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "needs_onboarding": True,
    "search_for_updates": True,
    "show_splash_screen": True,
    "user_name": "",
    "fancy_graphics": True,
    "show_console": False,
    "disable_auto_save": False,
    "disable_delete_confirm": False,
    "show_button_tooltips": True,
    "clef_presets": {},
}

VALID_FILE_EXTS = {".symphony", ".wav", ".mid", ".mp3", ".flac", ".musicxml"}


def _load_config() -> dict:
    try:
        with open(APP_ROOT / "config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load YAML: {exc}")
        return {}


CONFIG = _load_config()

EXECUTABLE_NAME = "main.exe" if sys.platform == "win32" else "main"
if IS_FROZEN:
    INNER_DIST_PATH = APP_ROOT / "inner" / "dist"
else:
    INNER_DIST_PATH = APP_ROOT / "inner" / "src"
if CONFIG and not CONFIG.get("editorIsExe", True):
    EXECUTABLE_NAME = "main.py"
EXECUTABLE_PATH = INNER_DIST_PATH / EXECUTABLE_NAME

print(f"USER_DATA_PATH: {USER_DATA_PATH}")
print(f"EXECUTABLE_PATH: {EXECUTABLE_PATH}")

_main_window: webview.Window | None = None
_persist_editor = True
_editor_lock = threading.Lock()
_is_maximized = False
_prev_geometry: tuple[int, int, int, int] | None = None
_current_editor_child: subprocess.Popen | None = None
_current_runner_thread: threading.Thread | None = None
_runner_should_stop = threading.Event()


def _win_work_area() -> tuple[int, int, int, int] | None:
    """Return (x, y, width, height) of the primary monitor's work area
    (screen minus taskbar) on Windows, or None elsewhere/on failure."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
        rect = RECT()
        SPI_GETWORKAREA = 0x0030
        if not ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETWORKAREA, 0, ctypes.byref(rect), 0
        ):
            return None
        return (
            rect.left,
            rect.top,
            rect.right - rect.left,
            rect.bottom - rect.top,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"_win_work_area failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Disk helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def _write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _ensure_file(src: Path, dest: Path, default_content: Any | None = None) -> None:
    if dest.exists():
        return
    try:
        if src.exists():
            shutil.copyfile(src, dest)
        elif default_content is not None:
            _write_json(dest, default_content)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to copy default file: {src} -> {dest}: {exc}")


def _delete_file(file_path: str) -> dict:
    try:
        Path(file_path).unlink()
        if file_path.endswith(".symphony"):
            meta = Path(file_path[: -len(".symphony")] + ".json")
            if meta.exists():
                meta.unlink()
        return {"success": True}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


def _add_recently_viewed(file_path: str) -> None:
    if not file_path:
        return
    recent = _read_json(RECENTLY_VIEWED_PATH, [])
    if not isinstance(recent, list):
        recent = []
    name = os.path.basename(file_path)
    file_type = os.path.splitext(name)[1].lstrip(".").lower()
    entry = {"type": file_type, "name": name, "fileLocation": os.path.dirname(file_path)}
    recent = [r for r in recent if not (r.get("name") == entry["name"] and r.get("fileLocation") == entry["fileLocation"])]
    recent.insert(0, entry)
    if len(recent) > 15:
        recent = recent[:15]
    _write_json(RECENTLY_VIEWED_PATH, recent)


# ---------------------------------------------------------------------------
# Process-command protocol (file-based handshake with /inner editor)
# ---------------------------------------------------------------------------


def _do_process_command(symphony_file_path: str, command: str, extra_args: dict | None = None) -> dict:
    extra_args = extra_args or {}
    cmd_id = str(uuid.uuid4())
    project_folder = os.path.dirname(symphony_file_path)
    project_name = os.path.splitext(os.path.basename(symphony_file_path))[0]

    if command == "open" and symphony_file_path:
        try:
            _add_recently_viewed(symphony_file_path)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to add to recently viewed on open: {exc}")

    payload = {
        "command": command,
        "id": cmd_id,
        "pc_file_path": str(PROCESS_COMMAND_PATH),
        "args": {
            "project_file_name": project_name,
            "project_folder_path": project_folder,
            "symphony_data_path": str(USER_DATA_PATH),
            **extra_args,
        },
    }
    print(payload)
    _write_json(PROCESS_COMMAND_PATH, payload)

    time.sleep(1.0)

    max_wait_ms = 15000
    poll_interval_ms = 100
    waited = 0
    while waited < max_wait_ms:
        try:
            if PROCESS_COMMAND_PATH.exists():
                data = _read_json(PROCESS_COMMAND_PATH, None)
                if isinstance(data, dict) and data.get("id") == cmd_id and data.get("status"):
                    print(data)
                    return data
        except Exception:  # noqa: BLE001
            pass
        time.sleep(poll_interval_ms / 1000.0)
        waited += poll_interval_ms

    return _read_json(PROCESS_COMMAND_PATH, {"timeout": True})


def _spawn_editor() -> None:
    is_python_script = str(EXECUTABLE_PATH).endswith(".py")
    script_path = str(EXECUTABLE_PATH.resolve())
    command_path = str(PROCESS_COMMAND_PATH.resolve())
    source_path = str(INNER_DIST_PATH.resolve())

    if is_python_script:
        cmd_name = "pythonw" if sys.platform == "win32" else "python3"
        args = [cmd_name, "-u", script_path, source_path, command_path]
    else:
        args = [script_path, source_path, command_path]

    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        popen_kwargs["start_new_session"] = True

    def runner() -> None:
        global _current_editor_child
        while not _runner_should_stop.is_set():
            try:
                child = subprocess.Popen(args, **popen_kwargs)
                _current_editor_child = child
            except Exception as exc:  # noqa: BLE001
                print(f"Failed to spawn editor: {exc}")
                return

            def pump(stream, sink) -> None:
                try:
                    for line in iter(stream.readline, b""):
                        sink.write(line.decode(errors="replace"))
                        sink.flush()
                except Exception:  # noqa: BLE001
                    pass

            threading.Thread(target=pump, args=(child.stdout, sys.stdout), daemon=True).start()
            threading.Thread(target=pump, args=(child.stderr, sys.stderr), daemon=True).start()

            code = child.wait()
            _current_editor_child = None
            if code != 0:
                print(f"Editor process crashed with code {code}.")
            else:
                print("Editor process exited.")
            if _runner_should_stop.is_set() or not _persist_editor:
                print("Runner exiting.")
                return
            print("Restarting...")

    global _current_runner_thread
    _runner_should_stop.clear()
    _current_runner_thread = threading.Thread(target=runner, daemon=True)
    _current_runner_thread.start()


def _editor_is_running() -> bool:
    child = _current_editor_child
    if child is None:
        return False
    return child.poll() is None


def _stop_editor() -> None:
    """Signal any active runner to stop and terminate its child subprocess."""
    global _current_editor_child, _current_runner_thread
    _runner_should_stop.set()
    child = _current_editor_child
    if child and child.poll() is None:
        # Cooperative shutdown via the file-based handshake first.
        try:
            _write_json(PROCESS_COMMAND_PATH, {"command": "kill"})
        except Exception as exc:  # noqa: BLE001
            print(f"kill write failed: {exc}")
        try:
            child.wait(timeout=2)
        except Exception:  # noqa: BLE001
            try:
                child.terminate()
                child.wait(timeout=2)
            except Exception:  # noqa: BLE001
                try:
                    child.kill()
                except Exception:  # noqa: BLE001
                    pass
    thread = _current_runner_thread
    if thread and thread.is_alive():
        thread.join(timeout=3)
    _current_editor_child = None
    _current_runner_thread = None


def _run_editor_program() -> dict:
    with _editor_lock:
        try:
            if _editor_is_running():
                return {"success": True, "message": "Editor already running"}
            _stop_editor()
            try:
                _write_json(PROCESS_COMMAND_PATH, {})
            except Exception:  # noqa: BLE001
                pass
            _spawn_editor()
            return {"success": True, "message": "Editor daemon started"}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# JS-API surface
# ---------------------------------------------------------------------------


class Api:
    """All methods here are callable from JS as ``window.pywebview.api.<name>``.

    The shim in ``src/electron-api-shim.js`` re-exports each one under the
    legacy ``window.electronAPI`` name used by the existing React code.
    """

    # ---- platform / window controls -------------------------------------
    def get_platform(self) -> str:
        # mirror Node's process.platform values
        if sys.platform.startswith("win"):
            return "win32"
        if sys.platform == "darwin":
            return "darwin"
        return "linux"

    def minimize(self) -> None:
        if _main_window:
            _main_window.minimize()

    def maximize(self) -> None:
        global _is_maximized, _prev_geometry
        if not _main_window:
            return
        # On Windows the frameless WinForms backend's native maximize covers
        # the taskbar (fullscreen-like). Resize/move to the work area instead
        # so it behaves like a normal Win32 maximize.
        if sys.platform == "win32":
            try:
                if _is_maximized and _prev_geometry:
                    x, y, w, h = _prev_geometry
                    _main_window.move(x, y)
                    _main_window.resize(w, h)
                    _is_maximized = False
                    _on_restored()
                    return
                work = _win_work_area()
                if not work:
                    _main_window.maximize()
                    return
                try:
                    _prev_geometry = (
                        int(_main_window.x),
                        int(_main_window.y),
                        int(_main_window.width),
                        int(_main_window.height),
                    )
                except Exception:  # noqa: BLE001
                    _prev_geometry = (100, 100, 1300, 800)
                wx, wy, ww, wh = work
                _main_window.move(wx, wy)
                _main_window.resize(ww, wh)
                _is_maximized = True
                _on_maximized()
                return
            except Exception as exc:  # noqa: BLE001
                print(f"maximize failed: {exc}")
                return
        # Non-Windows fallback
        try:
            if getattr(_main_window, "maximized", False):
                _main_window.restore()
            else:
                _main_window.maximize()
        except Exception:  # noqa: BLE001
            _main_window.maximize()

    def close(self) -> None:
        # destroy() does not fire the ``closing`` event on pywebview, so the
        # editor-subprocess kill handshake never runs. Invoke it explicitly.
        try:
            _on_closing()
        except Exception as exc:  # noqa: BLE001
            print(f"_on_closing during close failed: {exc}")
        if _main_window:
            _main_window.destroy()

    def toggle_devtools(self) -> None:
        if not _main_window:
            return
        try:
            _main_window.show_inspector()
        except Exception:  # noqa: BLE001
            pass

    # ---- generic file ops ------------------------------------------------
    def open_external(self, url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            print(f"open_external failed: {exc}")

    def open_file_location(self, file_path: str) -> bool:
        folder = os.path.dirname(file_path)
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", folder.replace("/", "\\")])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:  # noqa: BLE001
            print(f"open_file_location failed: {exc}")
            return False
        return True

    def file_exists(self, file_path: str) -> bool:
        return Path(file_path).exists()

    def delete_file(self, file_path: str) -> dict:
        return _delete_file(file_path)

    def rename_file(self, payload: dict) -> dict:
        file_path = payload.get("filePath")
        new_name = payload.get("newName") or ""
        if not file_path:
            return {"success": False, "error": "filePath required"}
        directory = os.path.dirname(file_path)
        base = new_name
        ext = os.path.splitext(new_name)[1]
        if not ext:
            ext = ".symphony"
            base = new_name
        else:
            base = os.path.splitext(new_name)[0]
        candidate = base + ext
        counter = 1
        try:
            existing = set(os.listdir(directory))
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}
        while candidate in existing:
            candidate = f"{base} ({counter}){ext}"
            counter += 1
        try:
            new_path = os.path.join(directory, candidate)
            os.rename(file_path, new_path)
            if file_path.endswith(".symphony"):
                old_json = file_path[: -len(".symphony")] + ".json"
                new_json = new_path[: -len(".symphony")] + ".json"
                if os.path.exists(old_json):
                    os.rename(old_json, new_json)
            return {"success": True, "newFilePath": new_path}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def copy_file(self, src: str, dest: str) -> str:
        shutil.copyfile(src, dest)
        return "success"

    def move_file_raw(
        self,
        file_data_b64: str,
        file_name: str,
        destination_dir: str,
        original_file_path: str | None,
    ) -> dict:
        """Receive a base64-encoded payload from the shim and write to disk."""
        dest_path = os.path.join(destination_dir, file_name)
        try:
            buf = base64.b64decode(file_data_b64 or "")
            print(f"[move-file-raw] source buffer bytes={len(buf)}")
            with open(dest_path, "wb") as f:
                f.write(buf)
            dest_size = os.path.getsize(dest_path)
            print(f"[move-file-raw] dest file bytes={dest_size}")
            print(f"[move-file-raw] originalFilePath={original_file_path or 'N/A'}")
            deleted_original = False
            if original_file_path:
                if os.path.abspath(original_file_path) == os.path.abspath(dest_path):
                    print("[move-file-raw] Source and destination are the same path; skipping delete.")
                    return {"success": True, "deletedOriginal": False}
                try:
                    src_size = os.path.getsize(original_file_path)
                except Exception:
                    src_size = -1
                same_size = src_size == dest_size
                print(f"[move-file-raw] sizeEqual={same_size}")
                if same_size:
                    res = _delete_file(original_file_path)
                    if not res.get("success"):
                        print(f"[move-file-raw] delete failed: {res.get('error')}")
                    deleted_original = bool(res.get("success"))
            return {"success": True, "deletedOriginal": deleted_original}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ---- directory ops ---------------------------------------------------
    def open_directory(self) -> str | None:
        if not _main_window:
            return None
        result = _main_window.create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return None
        return result[0] if isinstance(result, (list, tuple)) else result

    def save_directory(self, payload: dict) -> dict:
        destination = payload.get("destination")
        project_name = payload.get("projectName")
        source_location = payload.get("sourceLocation")
        try:
            directory = _read_json(DIRECTORY_PATH, {})
            if destination not in directory:
                directory[destination] = []
            name_exists = any(project_name in entry for entry in directory[destination])
            location_exists = any(
                source_location in entry.values() for entry in directory[destination]
            )
            if name_exists or location_exists:
                return {"success": False, "error": "Duplicate entry"}
            directory[destination].append({project_name: source_location})
            _write_json(DIRECTORY_PATH, directory)
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def get_directory(self) -> dict:
        try:
            if not DIRECTORY_PATH.exists():
                default = {"Projects": [], "Exports": [], "Symphony Auto-Save": []}
                _write_json(DIRECTORY_PATH, default)
                return default
            return _read_json(DIRECTORY_PATH, {})
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def remove_directory(self, section: str, dir_name: str) -> dict:
        try:
            if not DIRECTORY_PATH.exists():
                return {"success": False, "error": "directory.json not found"}
            directory = _read_json(DIRECTORY_PATH, {})
            if section not in directory:
                return {"success": False, "error": "Section not found"}
            directory[section] = [
                obj for obj in directory[section] if next(iter(obj.keys())) != dir_name
            ]
            _write_json(DIRECTORY_PATH, directory)
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def get_section_for_path(self, file_path: str) -> dict:
        try:
            if not DIRECTORY_PATH.exists():
                return {"error": "Directory data not found."}
            directory = _read_json(DIRECTORY_PATH, {})
            normalized = file_path.replace("\\", "/")
            for section, entries in directory.items():
                for entry in entries:
                    folder_path = next(iter(entry.values()))
                    if folder_path.replace("\\", "/") == normalized:
                        return {"section": section}
            return {"section": None, "message": "Path not found in any section."}
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def check_if_exists(self, data: dict) -> dict:
        # Mirror the (buggy) Electron handler signature, which only reports a
        # boolean. Used by EditModal.checkIfExists.
        try:
            destination = data.get("destination")
            project_name = data.get("projectName")
            source_location = data.get("sourceLocation")
            directory = _read_json(DIRECTORY_PATH, {})
            if destination not in directory:
                return {"success": True}
            entries = directory[destination]
            name_count = sum(1 for entry in entries if project_name in entry)
            location_count = sum(1 for entry in entries if source_location in entry.values())
            return {"success": (name_count > 0 or location_count > 0)}
        except Exception:  # noqa: BLE001
            return {"success": False}

    # ---- recently viewed -------------------------------------------------
    def get_recently_viewed(self) -> list:
        try:
            if not RECENTLY_VIEWED_PATH.exists():
                _write_json(RECENTLY_VIEWED_PATH, [])
            return _read_json(RECENTLY_VIEWED_PATH, [])
        except Exception:  # noqa: BLE001
            return []

    def recently_viewed_delete(self, file_name: str, file_location: str | None = None) -> dict:
        try:
            if not RECENTLY_VIEWED_PATH.exists():
                return {"success": False, "error": "recently-viewed.json not found"}
            recent = _read_json(RECENTLY_VIEWED_PATH, [])
            original = len(recent)
            if file_location:
                recent = [
                    item for item in recent
                    if not (item.get("name") == file_name and item.get("fileLocation") == file_location)
                ]
            else:
                recent = [item for item in recent if item.get("name") != file_name]
            if len(recent) == original:
                return {"success": False, "error": "Entry not found"}
            _write_json(RECENTLY_VIEWED_PATH, recent)
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def clear_recently_viewed(self) -> dict:
        try:
            _write_json(RECENTLY_VIEWED_PATH, [])
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ---- stars -----------------------------------------------------------
    def get_stars(self) -> list:
        try:
            if not STARRED_PATH.exists():
                _write_json(STARRED_PATH, [])
            return _read_json(STARRED_PATH, [])
        except Exception:  # noqa: BLE001
            return []

    def add_star(self, file_path: str) -> list:
        try:
            if not STARRED_PATH.exists():
                _write_json(STARRED_PATH, [])
            stars = _read_json(STARRED_PATH, [])
            normalized = file_path.replace("\\", "/")
            if not any(s.replace("\\", "/") == normalized for s in stars):
                stars.append(file_path)
                _write_json(STARRED_PATH, stars)
            return stars
        except Exception:  # noqa: BLE001
            return []

    def remove_star(self, file_path: str) -> list:
        try:
            if not STARRED_PATH.exists():
                _write_json(STARRED_PATH, [])
            stars = _read_json(STARRED_PATH, [])
            normalized = file_path.replace("\\", "/")
            stars = [s for s in stars if s.replace("\\", "/") != normalized]
            _write_json(STARRED_PATH, stars)
            return stars
        except Exception:  # noqa: BLE001
            return []

    # ---- user settings ---------------------------------------------------
    def get_user_settings(self) -> dict:
        # Read-only: many components call this concurrently at mount time, and
        # any write-back here races with update_user_settings() and clobbers
        # fields that were just set (e.g. user_name during onboarding).
        try:
            user_settings: dict[str, Any] = {}
            if USER_SETTINGS_PATH.exists():
                user_settings = _read_json(USER_SETTINGS_PATH, {})
            user_settings.pop("close_project_manager_when_editing", None)
            return {**DEFAULT_SETTINGS, **user_settings}
        except Exception as exc:  # noqa: BLE001
            print(f"Error reading user settings: {exc}")
            return dict(DEFAULT_SETTINGS)

    def update_user_settings(self, key: str, value: Any) -> dict:
        try:
            settings = _read_json(USER_SETTINGS_PATH, {})
            settings[key] = value
            _write_json(USER_SETTINGS_PATH, settings)
            return {"success": True, "settings": settings}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def fetch_json(self, url: str, options: dict | None = None) -> dict:
        options = options or {}
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Unsupported protocol: {parsed.scheme}")
            method = options.get("method", "GET")
            headers = options.get("headers") or {}
            body = options.get("body")
            data = body.encode("utf-8") if isinstance(body, str) else body
            req = urlrequest.Request(url, data=data, headers=headers, method=method)
            with urlrequest.urlopen(req, timeout=15) as resp:
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status}")
                return {"success": True, "data": json.loads(resp.read().decode("utf-8"))}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ---- symphony files --------------------------------------------------
    def get_symphony_files(self, directory_path: str) -> Any:
        try:
            files = os.listdir(directory_path)
            return [f for f in files if os.path.splitext(f)[1] in VALID_FILE_EXTS]
        except Exception:  # noqa: BLE001
            return "not a valid dir"

    def open_native_app(self, file_path: str) -> dict:
        try:
            if sys.platform == "win32":
                os.startfile(file_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
            try:
                _add_recently_viewed(file_path)
            except Exception as exc:  # noqa: BLE001
                return {"success": False, "error": str(exc)}
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ---- drag-out (best effort) -----------------------------------------
    def start_file_drag(self, file_path: str) -> None:
        # PyWebview has no native drag-source. The shim attempts a Chromium
        # HTML5 ``DownloadURL`` drag on the JS side; this Python call exists
        # only so the API surface matches Electron's preload.
        print(f"start_file_drag (no-op in pywebview): {file_path}")

    # ---- editor daemon ---------------------------------------------------
    def run_editor_program(self) -> dict:
        return _run_editor_program()

    # Alias to match the preload's (broken) channel name.
    def open_editor_program(self) -> dict:
        return _run_editor_program()

    def do_process_command(
        self,
        symphony_file_path: str,
        command: str,
        extra_args: dict | None = None,
    ) -> dict:
        return _do_process_command(symphony_file_path, command, extra_args or {})


# ---------------------------------------------------------------------------
# Window lifecycle
# ---------------------------------------------------------------------------


def _on_maximized() -> None:
    if _main_window:
        _main_window.evaluate_js(
            "window.__symphony_emit_window_state && window.__symphony_emit_window_state(true)"
        )


def _on_restored() -> None:
    if _main_window:
        _main_window.evaluate_js(
            "window.__symphony_emit_window_state && window.__symphony_emit_window_state(false)"
        )


def _on_closing() -> bool:
    global _persist_editor
    _persist_editor = False
    print("--> Stopping editor subprocess..")
    try:
        _stop_editor()
    except Exception as exc:  # noqa: BLE001
        print(f"_stop_editor failed: {exc}")
    return True


READY_MARKER = "__SYMPHONY_READY__"


def _on_loaded() -> None:
    # Signal the Tauri launcher (if any) that the pywebview window is up so it
    # can hide its splash. Safe to emit unconditionally; standalone runs just
    # see an extra log line.
    print(READY_MARKER, flush=True)
    # The ``loaded`` event fires on every page load, including Ctrl+R reloads.
    # Only start the editor when nothing is already running; otherwise reloads
    # would stack up duplicate runner threads and subprocesses.
    if _editor_is_running():
        return
    threading.Thread(target=lambda: print(_run_editor_program()), daemon=True).start()


def _check_vite(retries: int = 20, delay: float = 0.5) -> bool:
    for _ in range(retries):
        try:
            urlrequest.urlopen("http://localhost:5173", timeout=0.5)
            return True
        except Exception:  # noqa: BLE001
            time.sleep(delay)
    return False


def _resolve_url() -> str:
    if IS_FROZEN:
        return str((APP_ROOT / "dist" / "index.html").resolve())
    if os.environ.get("SYMPHONY_DEV", "1") != "0" and _check_vite():
        return "http://localhost:5173"
    dist_index = APP_ROOT / "dist" / "index.html"
    if dist_index.exists():
        return str(dist_index.resolve())
    return "http://localhost:5173"


def main() -> None:
    global _main_window

    asset_dir = APP_ROOT / "src" / "assets"
    _ensure_file(asset_dir / "user-settings.json", USER_SETTINGS_PATH, DEFAULT_SETTINGS)
    _ensure_file(
        asset_dir / "directory.json",
        DIRECTORY_PATH,
        {"Projects": [], "Exports": [], "Symphony Auto-Save": []},
    )
    _ensure_file(asset_dir / "starred.json", STARRED_PATH, [])
    _ensure_file(asset_dir / "recently-viewed.json", RECENTLY_VIEWED_PATH, [])

    api = Api()
    _main_window = webview.create_window(
        "Symphony",
        url=_resolve_url(),
        js_api=api,
        width=1300,
        height=800,
        min_size=(800, 800),
        frameless=True,
        easy_drag=False,
    )
    _main_window.events.maximized += _on_maximized
    _main_window.events.restored += _on_restored
    _main_window.events.closing += _on_closing
    _main_window.events.loaded += _on_loaded

    webview.start(debug=not IS_FROZEN)


if __name__ == "__main__":
    main()
