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

import win_c_man as win_c

win_c.patch_webview_nonclient()


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


def loadConfig() -> dict:
    '''
    fields: none
    outputs: dict

    Loads the project configuration file, returning an empty dictionary if it cannot be read.
    '''
    try:
        with open(APP_ROOT / "config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load YAML: {exc}")
        return {}


CONFIG = loadConfig()

EXECUTABLE_NAME = "main.exe" if sys.platform == "win32" else "main"
if IS_FROZEN:
    # Packaged builds always run the bundled PyInstaller editor executable from
    # inner/dist/. config.yaml's editorIsExe is intentionally ignored here: a
    # frozen build has no Python interpreter on PATH, and inner/src/main.py is
    # not shipped in the sidecar payload, so falling back to "main.py" would
    # leave the editor unable to launch.
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


# ---------------------------------------------------------------------------
# Disk helpers
# ---------------------------------------------------------------------------


def readJson(path: Path, default: Any) -> Any:
    '''
    fields:
        path (Path) - JSON file to read
        default (Any) - value to return when reading fails
    outputs: Any

    Reads JSON from disk and falls back to the provided default on any failure.
    '''
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def writeJson(path: Path, data: Any) -> None:
    '''
    fields:
        path (Path) - JSON file to write
        data (Any) - serializable data to save
    outputs: nothing

    Writes JSON data to disk with stable indentation.
    '''
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def ensureFile(src: Path, dest: Path, default_content: Any | None = None) -> None:
    '''
    fields:
        src (Path) - source file to copy from
        dest (Path) - destination file to ensure exists
        default_content (Any) - fallback JSON content to write if no source exists
    outputs: nothing

    Ensures a user-data file exists by copying a bundled file or writing default content.
    '''
    if dest.exists():
        return
    try:
        if src.exists():
            shutil.copyfile(src, dest)
        elif default_content is not None:
            writeJson(dest, default_content)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to copy default file: {src} -> {dest}: {exc}")


def deleteFile(file_path: str) -> dict:
    '''
    fields:
        file_path (string) - file path to remove
    outputs: dict

    Deletes a file from disk and removes its sidecar metadata when applicable.
    '''
    try:
        Path(file_path).unlink()
        if file_path.endswith(".symphony"):
            meta = Path(file_path[: -len(".symphony")] + ".json")
            if meta.exists():
                meta.unlink()
        return {"success": True}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


def addRecentlyViewed(file_path: str) -> None:
    '''
    fields:
        file_path (string) - file path to add to the recent list
    outputs: nothing

    Adds a file to the recently viewed list, keeping the list unique and capped.
    '''
    if not file_path:
        return
    recent = readJson(RECENTLY_VIEWED_PATH, [])
    if not isinstance(recent, list):
        recent = []
    name = os.path.basename(file_path)
    file_type = os.path.splitext(name)[1].lstrip(".").lower()
    entry = {"type": file_type, "name": name, "fileLocation": os.path.dirname(file_path)}
    recent = [r for r in recent if not (r.get("name") == entry["name"] and r.get("fileLocation") == entry["fileLocation"])]
    recent.insert(0, entry)
    if len(recent) > 15:
        recent = recent[:15]
    writeJson(RECENTLY_VIEWED_PATH, recent)


# ---------------------------------------------------------------------------
# Process-command protocol (file-based handshake with /inner editor)
# ---------------------------------------------------------------------------


def doProcessCommand(symphony_file_path: str, command: str, extra_args: dict | None = None) -> dict:
    '''
    fields:
        symphony_file_path (string) - Symphony project file path to operate on
        command (string) - editor command to issue
        extra_args (dict) - additional command arguments
    outputs: dict

    Sends a file-based command to the inner editor and waits for the matching response.
    '''
    extra_args = extra_args or {}
    cmd_id = str(uuid.uuid4())
    project_folder = os.path.dirname(symphony_file_path)
    project_name = os.path.splitext(os.path.basename(symphony_file_path))[0]

    if command == "open" and symphony_file_path:
        try:
            addRecentlyViewed(symphony_file_path)
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
    writeJson(PROCESS_COMMAND_PATH, payload)

    time.sleep(1.0)

    max_wait_ms = 15000
    poll_interval_ms = 100
    waited = 0
    while waited < max_wait_ms:
        try:
            if PROCESS_COMMAND_PATH.exists():
                data = readJson(PROCESS_COMMAND_PATH, None)
                if isinstance(data, dict) and data.get("id") == cmd_id and data.get("status"):
                    print(data)
                    return data
        except Exception:  # noqa: BLE001
            pass
        time.sleep(poll_interval_ms / 1000.0)
        waited += poll_interval_ms

    return readJson(PROCESS_COMMAND_PATH, {"timeout": True})


def spawnEditor() -> None:
    '''
    fields: none
    outputs: nothing

    Starts the inner editor process in a monitored runner thread.
    '''
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
        '''
        fields: none
        outputs: nothing

        Runs and restarts the editor child process until the runner is stopped.
        '''
        global _current_editor_child
        while not _runner_should_stop.is_set():
            try:
                child = subprocess.Popen(args, **popen_kwargs)
                _current_editor_child = child
            except Exception as exc:  # noqa: BLE001
                print(f"Failed to spawn editor: {exc}")
                return

            def pump(stream, sink) -> None:
                '''
                fields:
                    stream (file-like) - subprocess output stream to read
                    sink (file-like) - output stream to write decoded lines into
                outputs: nothing

                Forwards subprocess output into the parent process stream.
                '''
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


def editorIsRunning() -> bool:
    '''
    fields: none
    outputs: boolean

    Returns whether the tracked editor child process is still running.
    '''
    child = _current_editor_child
    if child is None:
        return False
    return child.poll() is None


def stopEditor() -> None:
    '''
    fields: none
    outputs: nothing

    Signals any active runner to stop and terminates its child subprocess.
    '''
    global _current_editor_child, _current_runner_thread
    _runner_should_stop.set()
    child = _current_editor_child
    if child and child.poll() is None:
        # Cooperative shutdown via the file-based handshake first.
        try:
            writeJson(PROCESS_COMMAND_PATH, {"command": "kill"})
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


def runEditorProgram() -> dict:
    '''
    fields: none
    outputs: dict

    Starts the editor daemon if it is not already running.
    '''
    with _editor_lock:
        try:
            if editorIsRunning():
                return {"success": True, "message": "Editor already running"}
            stopEditor()
            try:
                writeJson(PROCESS_COMMAND_PATH, {})
            except Exception:  # noqa: BLE001
                pass
            spawnEditor()
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
    def getPlatform(self) -> str:
        '''
        fields: none
        outputs: string

        Returns the current platform name using the legacy Electron platform values.
        '''
        # mirror Node's process.platform values
        if sys.platform.startswith("win"):
            return "win32"
        if sys.platform == "darwin":
            return "darwin"
        return "linux"

    def minimize(self) -> None:
        '''
        fields: none
        outputs: nothing

        Minimizes the application window.
        '''
        if _main_window:
            _main_window.minimize()

    def maximize(self) -> None:
        '''
        fields: none
        outputs: nothing

        Toggles the application window between maximized and restored states.
        '''
        global _is_maximized, _prev_geometry
        if not _main_window:
            return
        # The Windows WndProc constrains native maximize to the monitor work
        # area, so ShowWindow can keep the standard Aero animation.
        if sys.platform == "win32":
            try:
                maximized = win_c.toggle_native_maximize(_main_window)
                if maximized is None:
                    _main_window.maximize()
                    return
                _is_maximized = maximized
                if maximized:
                    onMaximized()
                else:
                    onRestored()
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
        '''
        fields: none
        outputs: nothing

        Stops the editor process and closes the application window.
        '''
        # destroy() does not fire the ``closing`` event on pywebview, so the
        # editor-subprocess kill handshake never runs. Invoke it explicitly.
        try:
            onClosing()
        except Exception as exc:  # noqa: BLE001
            print(f"onClosing during close failed: {exc}")
        if _main_window:
            _main_window.destroy()

    def toggleDevtools(self) -> None:
        '''
        fields: none
        outputs: nothing

        Opens the webview inspector when it is available.
        '''
        if not _main_window:
            return
        try:
            _main_window.show_inspector()
        except Exception:  # noqa: BLE001
            pass

    def startWindowResize(self, edge: str) -> bool:
        '''
        fields:
            edge (string) - Resize edge or corner name.
        outputs: boolean

        Starts the native Windows resize loop for frameless WebView windows.
        '''
        if sys.platform != "win32":
            return False
        return win_c.start_resize(_main_window, edge)

    def beginManualWindowResize(self, edge: str, screen_x: int, screen_y: int) -> bool:
        '''
        fields:
            edge (string) - Resize edge or corner name.
            screen_x (number) - Mouse screen X at drag start.
            screen_y (number) - Mouse screen Y at drag start.
        outputs: boolean

        Captures initial geometry for JS-driven resize handles.
        '''
        if sys.platform != "win32":
            return False
        return win_c.begin_manual_resize(_main_window, edge, screen_x, screen_y)

    def updateManualWindowResize(self, screen_x: int, screen_y: int) -> bool:
        '''
        fields:
            screen_x (number) - Current mouse screen X.
            screen_y (number) - Current mouse screen Y.
        outputs: boolean

        Applies a JS-driven resize update.
        '''
        if sys.platform != "win32":
            return False
        return win_c.update_manual_resize(_main_window, screen_x, screen_y)

    def endManualWindowResize(self) -> None:
        '''
        fields: none
        outputs: nothing

        Clears JS-driven resize state.
        '''
        win_c.end_manual_resize()

    # ---- generic file ops ------------------------------------------------
    def openExternal(self, url: str) -> None:
        '''
        fields:
            url (string) - URL to open
        outputs: nothing

        Opens an external URL using the operating system browser.
        '''
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            print(f"openExternal failed: {exc}")

    def openFileLocation(self, file_path: str) -> bool:
        '''
        fields:
            file_path (string) - file whose parent folder should be shown
        outputs: boolean

        Opens the native file manager to the folder containing a file.
        '''
        folder = os.path.dirname(file_path)
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", folder.replace("/", "\\")])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:  # noqa: BLE001
            print(f"openFileLocation failed: {exc}")
            return False
        return True

    def fileExists(self, file_path: str) -> bool:
        '''
        fields:
            file_path (string) - file path to check
        outputs: boolean

        Returns whether the supplied file path exists on disk.
        '''
        return Path(file_path).exists()

    def deleteFile(self, file_path: str) -> dict:
        '''
        fields:
            file_path (string) - file path to delete
        outputs: dict

        Deletes a file through the shared disk helper.
        '''
        return deleteFile(file_path)

    def renameFile(self, payload: dict) -> dict:
        '''
        fields:
            payload (dict) - filePath and newName values for the rename
        outputs: dict

        Renames a file while avoiding name collisions and preserving sidecar metadata.
        '''
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

    def copyFile(self, src: str, dest: str) -> str:
        '''
        fields:
            src (string) - source file path
            dest (string) - destination file path
        outputs: string

        Copies one file to another path.
        '''
        shutil.copyfile(src, dest)
        return "success"

    def moveFileRaw(
        self,
        file_data_b64: str,
        file_name: str,
        destination_dir: str,
        original_file_path: str | None,
    ) -> dict:
        '''
        fields:
            file_data_b64 (string) - base64-encoded file contents
            file_name (string) - destination file name
            destination_dir (string) - directory to write the file into
            original_file_path (string) - optional original file path to remove after moving
        outputs: dict

        Receives a base64-encoded payload from the shim and writes it to disk.
        '''
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
                    res = deleteFile(original_file_path)
                    if not res.get("success"):
                        print(f"[move-file-raw] delete failed: {res.get('error')}")
                    deleted_original = bool(res.get("success"))
            return {"success": True, "deletedOriginal": deleted_original}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ---- directory ops ---------------------------------------------------
    def openDirectory(self) -> str | None:
        '''
        fields: none
        outputs: string | None

        Opens a native folder picker and returns the selected directory path.
        '''
        if not _main_window:
            return None
        result = _main_window.create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return None
        return result[0] if isinstance(result, (list, tuple)) else result

    def saveDirectory(self, payload: dict) -> dict:
        '''
        fields:
            payload (dict) - destination, projectName, and sourceLocation values
        outputs: dict

        Saves a project directory entry after checking for duplicates.
        '''
        destination = payload.get("destination")
        project_name = payload.get("projectName")
        source_location = payload.get("sourceLocation")
        try:
            directory = readJson(DIRECTORY_PATH, {})
            if destination not in directory:
                directory[destination] = []
            name_exists = any(project_name in entry for entry in directory[destination])
            location_exists = any(
                source_location in entry.values() for entry in directory[destination]
            )
            if name_exists or location_exists:
                return {"success": False, "error": "Duplicate entry"}
            directory[destination].append({project_name: source_location})
            writeJson(DIRECTORY_PATH, directory)
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def getDirectory(self) -> dict:
        '''
        fields: none
        outputs: dict

        Returns the saved project directory structure, creating defaults if needed.
        '''
        try:
            if not DIRECTORY_PATH.exists():
                default = {"Projects": [], "Exports": [], "Symphony Auto-Save": []}
                writeJson(DIRECTORY_PATH, default)
                return default
            return readJson(DIRECTORY_PATH, {})
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def removeDirectory(self, section: str, dir_name: str) -> dict:
        '''
        fields:
            section (string) - directory section to edit
            dir_name (string) - directory display name to remove
        outputs: dict

        Removes a directory entry from a saved section.
        '''
        try:
            if not DIRECTORY_PATH.exists():
                return {"success": False, "error": "directory.json not found"}
            directory = readJson(DIRECTORY_PATH, {})
            if section not in directory:
                return {"success": False, "error": "Section not found"}
            directory[section] = [
                obj for obj in directory[section] if next(iter(obj.keys())) != dir_name
            ]
            writeJson(DIRECTORY_PATH, directory)
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def getSectionForPath(self, file_path: str) -> dict:
        '''
        fields:
            file_path (string) - folder path to search for
        outputs: dict

        Finds which directory section contains the supplied folder path.
        '''
        try:
            if not DIRECTORY_PATH.exists():
                return {"error": "Directory data not found."}
            directory = readJson(DIRECTORY_PATH, {})
            normalized = file_path.replace("\\", "/")
            for section, entries in directory.items():
                for entry in entries:
                    folder_path = next(iter(entry.values()))
                    if folder_path.replace("\\", "/") == normalized:
                        return {"section": section}
            return {"section": None, "message": "Path not found in any section."}
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def checkIfExists(self, data: dict) -> dict:
        '''
        fields:
            data (dict) - destination, projectName, and sourceLocation values to check
        outputs: dict

        Checks whether a directory entry already exists using the legacy response shape.
        '''
        # Mirror the (buggy) Electron handler signature, which only reports a
        # boolean. Used by EditModal.checkIfExists.
        try:
            destination = data.get("destination")
            project_name = data.get("projectName")
            source_location = data.get("sourceLocation")
            directory = readJson(DIRECTORY_PATH, {})
            if destination not in directory:
                return {"success": True}
            entries = directory[destination]
            name_count = sum(1 for entry in entries if project_name in entry)
            location_count = sum(1 for entry in entries if source_location in entry.values())
            return {"success": (name_count > 0 or location_count > 0)}
        except Exception:  # noqa: BLE001
            return {"success": False}

    # ---- recently viewed -------------------------------------------------
    def getRecentlyViewed(self) -> list:
        '''
        fields: none
        outputs: list

        Returns the recently viewed file entries, creating the store if needed.
        '''
        try:
            if not RECENTLY_VIEWED_PATH.exists():
                writeJson(RECENTLY_VIEWED_PATH, [])
            return readJson(RECENTLY_VIEWED_PATH, [])
        except Exception:  # noqa: BLE001
            return []

    def recentlyViewedDelete(self, file_name: str, file_location: str | None = None) -> dict:
        '''
        fields:
            file_name (string) - recent item file name to remove
            file_location (string) - optional folder path to disambiguate the entry
        outputs: dict

        Removes an entry from the recently viewed file list.
        '''
        try:
            if not RECENTLY_VIEWED_PATH.exists():
                return {"success": False, "error": "recently-viewed.json not found"}
            recent = readJson(RECENTLY_VIEWED_PATH, [])
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
            writeJson(RECENTLY_VIEWED_PATH, recent)
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def clearRecentlyViewed(self) -> dict:
        '''
        fields: none
        outputs: dict

        Clears all recently viewed file entries.
        '''
        try:
            writeJson(RECENTLY_VIEWED_PATH, [])
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ---- stars -----------------------------------------------------------
    def getStars(self) -> list:
        '''
        fields: none
        outputs: list

        Returns the saved starred file paths, creating the store if needed.
        '''
        try:
            if not STARRED_PATH.exists():
                writeJson(STARRED_PATH, [])
            return readJson(STARRED_PATH, [])
        except Exception:  # noqa: BLE001
            return []

    def addStar(self, file_path: str) -> list:
        '''
        fields:
            file_path (string) - file path to star
        outputs: list

        Adds a file path to the starred list if it is not already present.
        '''
        try:
            if not STARRED_PATH.exists():
                writeJson(STARRED_PATH, [])
            stars = readJson(STARRED_PATH, [])
            normalized = file_path.replace("\\", "/")
            if not any(s.replace("\\", "/") == normalized for s in stars):
                stars.append(file_path)
                writeJson(STARRED_PATH, stars)
            return stars
        except Exception:  # noqa: BLE001
            return []

    def removeStar(self, file_path: str) -> list:
        '''
        fields:
            file_path (string) - file path to unstar
        outputs: list

        Removes a file path from the starred list.
        '''
        try:
            if not STARRED_PATH.exists():
                writeJson(STARRED_PATH, [])
            stars = readJson(STARRED_PATH, [])
            normalized = file_path.replace("\\", "/")
            stars = [s for s in stars if s.replace("\\", "/") != normalized]
            writeJson(STARRED_PATH, stars)
            return stars
        except Exception:  # noqa: BLE001
            return []

    # ---- user settings ---------------------------------------------------
    def getUserSettings(self) -> dict:
        '''
        fields: none
        outputs: dict

        Returns user settings merged over defaults without mutating the settings file.
        '''
        # Read-only: many components call this concurrently at mount time, and
        # any write-back here races with updateUserSettings() and clobbers
        # fields that were just set (e.g. user_name during onboarding).
        try:
            user_settings: dict[str, Any] = {}
            if USER_SETTINGS_PATH.exists():
                user_settings = readJson(USER_SETTINGS_PATH, {})
            user_settings.pop("close_project_manager_when_editing", None)
            return {**DEFAULT_SETTINGS, **user_settings}
        except Exception as exc:  # noqa: BLE001
            print(f"Error reading user settings: {exc}")
            return dict(DEFAULT_SETTINGS)

    def updateUserSettings(self, key: str, value: Any) -> dict:
        '''
        fields:
            key (string) - settings key to update
            value (Any) - settings value to store
        outputs: dict

        Updates a single user setting in the persisted settings file.
        '''
        try:
            settings = readJson(USER_SETTINGS_PATH, {})
            settings[key] = value
            writeJson(USER_SETTINGS_PATH, settings)
            return {"success": True, "settings": settings}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    def fetchJson(self, url: str, options: dict | None = None) -> dict:
        '''
        fields:
            url (string) - HTTP or HTTPS URL to fetch
            options (dict) - request method, headers, and optional body
        outputs: dict

        Fetches JSON over HTTP for the frontend while validating the protocol.
        '''
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
    def getSymphonyFiles(self, directory_path: str) -> Any:
        '''
        fields:
            directory_path (string) - directory to scan
        outputs: Any

        Returns Symphony-compatible files from a directory or a legacy error string.
        '''
        try:
            files = os.listdir(directory_path)
            return [f for f in files if os.path.splitext(f)[1] in VALID_FILE_EXTS]
        except Exception:  # noqa: BLE001
            return "not a valid dir"

    def openNativeApp(self, file_path: str) -> dict:
        '''
        fields:
            file_path (string) - file path to open
        outputs: dict

        Opens a file with the operating system default application and records it as recent.
        '''
        try:
            if sys.platform == "win32":
                os.startfile(file_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
            try:
                addRecentlyViewed(file_path)
            except Exception as exc:  # noqa: BLE001
                return {"success": False, "error": str(exc)}
            return {"success": True}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ---- drag-out (best effort) -----------------------------------------
    def startFileDrag(self, file_path: str) -> None:
        '''
        fields:
            file_path (string) - file path being dragged
        outputs: nothing

        Keeps the drag API surface aligned with the Electron preload while doing no native work.
        '''
        # PyWebview has no native drag-source. The shim attempts a Chromium
        # HTML5 ``DownloadURL`` drag on the JS side; this Python call exists
        # only so the API surface matches Electron's preload.
        print(f"start_file_drag (no-op in pywebview): {file_path}")

    # ---- editor daemon ---------------------------------------------------
    def runEditorProgram(self) -> dict:
        '''
        fields: none
        outputs: dict

        Starts the editor daemon through the shared runner helper.
        '''
        return runEditorProgram()

    # Alias to match the preload's (broken) channel name.
    def openEditorProgram(self) -> dict:
        '''
        fields: none
        outputs: dict

        Starts the editor daemon using the legacy open-editor channel.
        '''
        return runEditorProgram()

    def doProcessCommand(
        self,
        symphony_file_path: str,
        command: str,
        extra_args: dict | None = None,
    ) -> dict:
        '''
        fields:
            symphony_file_path (string) - Symphony project file path to operate on
            command (string) - editor command to issue
            extra_args (dict) - additional command arguments
        outputs: dict

        Sends a command to the editor process through the process-command protocol.
        '''
        return doProcessCommand(symphony_file_path, command, extra_args or {})


# ---------------------------------------------------------------------------
# Window lifecycle
# ---------------------------------------------------------------------------


def onMaximized() -> None:
    '''
    fields: none
    outputs: nothing

    Emits a frontend event indicating the window is maximized.
    '''
    if _main_window:
        _main_window.evaluate_js(
            "window.__symphony_emit_window_state && window.__symphony_emit_window_state(true)"
        )


def onRestored() -> None:
    '''
    fields: none
    outputs: nothing

    Emits a frontend event indicating the window has been restored.
    '''
    if _main_window:
        _main_window.evaluate_js(
            "window.__symphony_emit_window_state && window.__symphony_emit_window_state(false)"
        )


def onClosing() -> bool:
    '''
    fields: none
    outputs: boolean

    Handles window shutdown by stopping the editor process before close completes.
    '''
    global _persist_editor
    _persist_editor = False
    print("--> Stopping editor subprocess..")
    try:
        stopEditor()
    except Exception as exc:  # noqa: BLE001
        print(f"stopEditor failed: {exc}")
    return True


READY_MARKER = "__SYMPHONY_READY__"


def onLoaded() -> None:
    '''
    fields: none
    outputs: nothing

    Handles webview load completion and starts the editor process when needed.
    '''
    # Signal the Tauri launcher (if any) that the pywebview window is up so it
    # can hide its splash. Safe to emit unconditionally; standalone runs just
    # see an extra log line.
    print(READY_MARKER, flush=True)
    if sys.platform == "win32":
        win_c.install_aero_and_resize(_main_window, lambda: Api().maximize())
    # The ``loaded`` event fires on every page load, including Ctrl+R reloads.
    # Only start the editor when nothing is already running; otherwise reloads
    # would stack up duplicate runner threads and subprocesses.
    if editorIsRunning():
        return
    threading.Thread(target=lambda: print(runEditorProgram()), daemon=True).start()


def checkVite(retries: int = 20, delay: float = 0.5) -> bool:
    '''
    fields:
        retries (number) - number of attempts to check the dev server
        delay (number) - seconds to wait between attempts
    outputs: boolean

    Returns whether the Vite dev server responds before the retry limit is reached.
    '''
    for _ in range(retries):
        try:
            urlrequest.urlopen("http://localhost:5173", timeout=0.5)
            return True
        except Exception:  # noqa: BLE001
            time.sleep(delay)
    return False


def resolveUrl() -> str:
    '''
    fields: none
    outputs: string

    Resolves the frontend URL or built index path the webview should load.
    '''
    if IS_FROZEN:
        return str((APP_ROOT / "dist" / "index.html").resolve())
    if os.environ.get("SYMPHONY_DEV", "1") != "0" and checkVite():
        return "http://localhost:5173"
    dist_index = APP_ROOT / "dist" / "index.html"
    if dist_index.exists():
        return str(dist_index.resolve())
    return "http://localhost:5173"


def main() -> None:
    '''
    fields: none
    outputs: nothing

    Creates the pywebview window, attaches lifecycle hooks, and starts the app event loop.
    '''
    global _main_window

    asset_dir = APP_ROOT / "src" / "assets"
    ensureFile(asset_dir / "user-settings.json", USER_SETTINGS_PATH, DEFAULT_SETTINGS)
    ensureFile(
        asset_dir / "directory.json",
        DIRECTORY_PATH,
        {"Projects": [], "Exports": [], "Symphony Auto-Save": []},
    )
    ensureFile(asset_dir / "starred.json", STARRED_PATH, [])
    ensureFile(asset_dir / "recently-viewed.json", RECENTLY_VIEWED_PATH, [])

    api = Api()
    _main_window = webview.create_window(
        "Symphony",
        url=resolveUrl(),
        js_api=api,
        width=1300,
        height=800,
        min_size=(800, 800),
        frameless=True,
        easy_drag=False,
    )
    _main_window.events.maximized += onMaximized
    _main_window.events.restored += onRestored
    _main_window.events.closing += onClosing
    _main_window.events.loaded += onLoaded

    if sys.platform == "win32":
        def winAeroDeferred():
            '''
            fields: none
            outputs: nothing

            Applies deferred Windows chrome fixes after pywebview finishes initializing.
            '''
            time.sleep(0.8)   # wait for WinForms to finish its own init
            win_c.install_aero_and_resize(_main_window, lambda: Api().maximize())
            # Activate resize grips by doing a 1-px nudge through pywebview's
            # own resize path (WinForms UI thread).  This is the same code path
            # maximize takes; our background-thread SetWindowPos alone is not
            # enough because WinForms marshals the actual style commit to the UI
            # thread and we need that commit to happen before grips are live.
            time.sleep(0.05)
            if _main_window:
                try:
                    w = int(_main_window.width)
                    h = int(_main_window.height)
                    _main_window.resize(w + 1, h)
                    time.sleep(0.05)
                    _main_window.resize(w, h)
                except Exception as exc:
                    print(f"startup grip nudge failed: {exc}")
        webview.start(debug=not IS_FROZEN, func=winAeroDeferred)
    else:
        webview.start(debug=not IS_FROZEN)


if __name__ == "__main__":
    main()
