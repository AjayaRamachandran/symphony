# /main.py

# Replaces the Electron main process (main.js). Renders the Vite frontend in a
# pywebview window and exposes a ``js_api`` whose method names are consumed by
# ``preload.js`` to provide ``window.electronAPI``.


from __future__ import annotations


import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

INNER_SRC_PATH = Path(__file__).resolve().parent / "inner" / "src"
if str(INNER_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(INNER_SRC_PATH))
from console_controls.console import console  # type: ignore[import]
from typing import Any
from urllib import request as urlrequest
from urllib.parse import urlparse

import webview
import yaml
from platformdirs import user_data_dir

if sys.platform == "win32":
    from winman import win64_winman as winman
elif sys.platform == "darwin":
    from winman import macos_winman as winman
else:
    class _NullWinC:
        """Linux fallback. Every attribute resolves to a no-op callable so
        main.py keeps its `winman.<fn>(...)` call surface platform-agnostic."""

        def __getattr__(self, _name):
            return lambda *_a, **_kw: None

    winman = _NullWinC()

if sys.platform == "darwin":
    try:
        from winman import native_drag_mac as native_drag
    except Exception as exc:  # noqa: BLE001
        console.log(f"native_drag_mac unavailable: {exc}")
        native_drag = None  # type: ignore[assignment]
else:
    native_drag = None  # type: ignore[assignment]


def nativeStartDrag(file_paths) -> bool:
    '''
    fields:
        file_paths (string | list) - one or more absolute file paths to drag
    outputs: boolean

    Dispatches a native OS file drag through the active platform backend.
    Posts to the UI thread on Windows so DoDragDrop runs on the same thread
    that owns the WebView's mouse capture (matches tauri-plugin-drag).
    '''
    if sys.platform == "win32":
        try:
            return bool(winman.post_native_drag(_main_window, file_paths))
        except Exception as exc:  # noqa: BLE001
            console.log(f"nativeStartDrag (win32) failed: {exc}")
            return False
    if sys.platform == "darwin" and native_drag is not None:
        try:
            return bool(native_drag.startFileDrag(file_paths))
        except Exception as exc:  # noqa: BLE001
            console.log(f"nativeStartDrag (darwin) failed: {exc}")
            return False
    return False


def nativeRegisterDrop(window, on_paths) -> bool:
    '''
    fields:
        window (Window) - host pywebview window to attach drop handling to
        on_paths (callable) - callback invoked with (paths, screenX, screenY)
    outputs: boolean

    Registers an OS-native drop target on the window for the active platform.
    '''
    if sys.platform == "win32":
        try:
            return bool(winman.register_drop_target(window, on_paths))
        except Exception as exc:  # noqa: BLE001
            console.log(f"nativeRegisterDrop (win32) failed: {exc}")
            return False
    if sys.platform == "darwin" and native_drag is not None:
        try:
            return bool(native_drag.registerDropTarget(window, on_paths))
        except Exception as exc:  # noqa: BLE001
            console.log(f"nativeRegisterDrop (darwin) failed: {exc}")
            return False
    return False


winman.patch_webview_nonclient()


APP_NAME = "Symphony"
# Windows AppUserModelID. Must match Tauri's ``identifier`` in
# ``src-tauri/tauri.conf.json`` and the ID assigned in the Rust launcher
# (``src-tauri/src/main.rs``) and the inner editor
# (``inner/src/utils/platform_controller.py``). The installer stamps this same
# ID onto the Symphony Start Menu / Desktop shortcuts, so when every visible
# HWND across the launcher, pywebview backend, and pygame editor declares it
# explicitly, Windows groups them all under the installed Symphony shortcut
# and right-click -> Pin to Start always pins the launcher, not this backend.
APP_USER_MODEL_ID = "com.ajayarsymphony.desktop"
IS_FROZEN = getattr(sys, "frozen", False)
APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def setAppUserModelId() -> None:
    '''
    fields: none
    outputs: nothing

    Binds this Python process to the canonical Symphony AppUserModelID on
    Windows. Must be invoked before any top-level HWND is created (pywebview
    window, file dialogs, etc.) so the taskbar associates them with the
    installed Symphony shortcut instead of ``symphony-backend.exe``.
    No-op on non-Windows platforms.
    '''
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll  # local import: Windows-only
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception as exc:  # noqa: BLE001
        console.log(f"setAppUserModelId failed: {exc}")


# ---------------------------------------------------------------------------
# Second-instance handoff (PM-owned localhost HTTP server)
# ---------------------------------------------------------------------------
#
# The Rust launcher uses tauri-plugin-single-instance to detect a duplicate
# Symphony.exe launch in the original Rust process. The original Rust process
# then POSTs to this server, which (a) focuses the pywebview window and
# (b) when a .symphony path is forwarded, queues it for the existing React
# PendingFileHandoff via the same _PENDING_OPEN_FILE channel used at startup.

def _pmPortFile() -> Path:
    # Lazy resolution: USER_DATA_PATH is defined later in this module, so
    # we can't bind this as a module-level constant up here without
    # reordering imports.
    return USER_DATA_PATH / "pm-port.txt"


def _writePmPortFile(port: int) -> None:
    try:
        _pmPortFile().write_text(str(int(port)), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        console.log(f"_writePmPortFile failed: {exc}")


def _removePmPortFile() -> None:
    try:
        path = _pmPortFile()
        if path.exists():
            path.unlink()
    except Exception as exc:  # noqa: BLE001
        console.log(f"_removePmPortFile failed: {exc}")


def _handleSecondInstance(payload: dict) -> None:
    '''
    fields:
        payload (dict) - decoded JSON body from the Rust launcher
    outputs: nothing

    Sets _PENDING_OPEN_FILE if a path was forwarded, focuses the main
    pywebview window, and dispatches a ``symphony:second-instance`` event
    to React so the PendingFileHandoff component can replay its flow.
    '''
    global _PENDING_OPEN_FILE, _PENDING_OPEN_FILE_IS_TEST_IMPORT
    path = payload.get("path") if isinstance(payload, dict) else None

    if isinstance(path, str) and path:
        try:
            abs_path = os.path.abspath(path)
        except Exception:  # noqa: BLE001
            abs_path = path
        with _pending_open_file_lock:
            _PENDING_OPEN_FILE = abs_path
            _PENDING_OPEN_FILE_IS_TEST_IMPORT = False
        console.log(f"second-instance: queued PENDING_OPEN_FILE={abs_path}")

    try:
        winman.focus_main_window(_main_window)
    except Exception as exc:  # noqa: BLE001
        console.log(f"second-instance focus_main_window failed: {exc}")

    if _main_window is not None:
        try:
            _main_window.evaluate_js(
                "window.dispatchEvent(new CustomEvent('symphony:second-instance'));"
            )
        except Exception as exc:  # noqa: BLE001
            console.log(f"second-instance evaluate_js failed: {exc}")


def startPmHandoffServer() -> None:
    '''
    fields: none
    outputs: nothing

    Starts a 127.0.0.1-only HTTP server on an ephemeral port, writes the
    chosen port to ``pm-port.txt`` in USER_DATA_PATH, and serves POST
    /instance for the Rust launcher's second-instance handoff. Idempotent:
    safe to call multiple times; subsequent calls are no-ops.
    '''
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    if getattr(startPmHandoffServer, "_started", False):
        return

    class HandoffHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 (http.server contract)
            if self.path != "/instance":
                self.send_response(404)
                self.end_headers()
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b""
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception as exc:  # noqa: BLE001
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"bad request: {exc}".encode("utf-8"))
                return
            try:
                _handleSecondInstance(payload)
            except Exception as exc:  # noqa: BLE001
                console.log(f"HandoffHandler: _handleSecondInstance failed: {exc}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{\"ok\":true}")

        def log_message(self, *_args, **_kwargs) -> None:
            # Silence the default stderr access log; the line-buffered
            # backend stdout already gets piped into launcher.log.
            return

    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), HandoffHandler)
    except Exception as exc:  # noqa: BLE001
        console.log(f"startPmHandoffServer: bind failed: {exc}")
        return

    port = server.server_address[1]
    _writePmPortFile(port)
    console.log(f"PM handoff server listening on 127.0.0.1:{port}")

    def serve() -> None:
        try:
            server.serve_forever(poll_interval=0.5)
        except Exception as exc:  # noqa: BLE001
            console.log(f"PM handoff server stopped: {exc}")

    thread = threading.Thread(target=serve, name="symphony-pm-handoff", daemon=True)
    thread.start()
    startPmHandoffServer._started = True  # type: ignore[attr-defined]

    import atexit

    atexit.register(_removePmPortFile)

USER_DATA_PATH = Path(user_data_dir(APP_NAME, appauthor=False, roaming=True))
USER_DATA_PATH.mkdir(parents=True, exist_ok=True)
DIRECTORY_PATH = USER_DATA_PATH / "directory.json"
RECENTLY_VIEWED_PATH = USER_DATA_PATH / "recently-viewed.json"
STARRED_PATH = USER_DATA_PATH / "starred.json"
USER_SETTINGS_PATH = USER_DATA_PATH / "user-settings.json"
PROCESS_COMMAND_HOST = "127.0.0.1"


def findAvailableLocalPort() -> int:
    '''
    fields: none
    outputs: int

    Reserves a free localhost port number for this backend/editor pair.
    '''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((PROCESS_COMMAND_HOST, 0))
        return int(sock.getsockname()[1])


PROCESS_COMMAND_PORT = int(os.environ.get("SYMPHONY_PROCESS_COMMAND_PORT") or findAvailableLocalPort())
PROCESS_COMMAND_URL = f"http://{PROCESS_COMMAND_HOST}:{PROCESS_COMMAND_PORT}/process-command"
PROCESS_COMMAND_HEALTH_URL = f"http://{PROCESS_COMMAND_HOST}:{PROCESS_COMMAND_PORT}/health"

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

# When the OS launches Symphony to open a .symphony file (file association),
# the Rust launcher forwards the resolved absolute path to this process via
# the SYMPHONY_OPEN_FILE environment variable. Dev can also set
# SYMPHONY_TEST_IMPORT to force the same startup handoff into the import modal.
# We capture it once at module load. ``Api.getPendingOpenFile`` clears it after
# the first successful read so a webview reload (Ctrl+R) doesn't replay the flow.
_pending_open_file_lock = threading.Lock()
_PENDING_OPEN_FILE_IS_TEST_IMPORT = bool(os.environ.get("SYMPHONY_TEST_IMPORT"))
_PENDING_OPEN_FILE: str | None = (
    os.path.abspath(os.environ["SYMPHONY_TEST_IMPORT"])
    if os.environ.get("SYMPHONY_TEST_IMPORT")
    else os.path.abspath(os.environ["SYMPHONY_OPEN_FILE"])
    if os.environ.get("SYMPHONY_OPEN_FILE")
    else None
)
if _PENDING_OPEN_FILE:
    console.log(f"PENDING_OPEN_FILE: {_PENDING_OPEN_FILE}")


def findFileInRegistry(file_path: str) -> dict | None:
    '''
    fields:
        file_path (string) - absolute path to a .symphony file
    outputs: dict | None

    Returns the directory.json entry whose registered folder is the direct
    parent of ``file_path`` (shallow match), searching all three sections.
    Returns ``None`` when no registered folder owns the file's parent.
    '''
    try:
        directory = readJson(DIRECTORY_PATH, {})
    except Exception as exc:  # noqa: BLE001
        console.log(f"findFileInRegistry: failed to read directory.json: {exc}")
        return None
    parent = os.path.normcase(os.path.normpath(os.path.dirname(file_path)))
    for section, entries in directory.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for alias, registered in entry.items():
                if not isinstance(registered, str):
                    continue
                normalized = os.path.normcase(os.path.normpath(registered))
                if normalized == parent:
                    return {"section": section, "name": alias, "dir": registered}
    return None


def isDirectoryRegistered(dir_path: str) -> bool:
    '''
    fields:
        dir_path (string) - absolute folder path to look up
    outputs: boolean

    Returns whether ``dir_path`` is registered in any section of directory.json.
    '''
    try:
        directory = readJson(DIRECTORY_PATH, {})
    except Exception:  # noqa: BLE001
        return False
    target = os.path.normcase(os.path.normpath(dir_path))
    for entries in directory.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for registered in entry.values():
                if not isinstance(registered, str):
                    continue
                if os.path.normcase(os.path.normpath(registered)) == target:
                    return True
    return False


def resolveCopyDestination(source_path: str, dest_dir: str) -> str:
    '''
    fields:
        source_path (string) - .symphony file to copy
        dest_dir (string) - destination folder
    outputs: string

    Returns an absolute destination path inside ``dest_dir`` that does not
    collide with an existing file, suffixing " (1)", " (2)", ... as needed
    while preserving the .symphony extension.
    '''
    base = os.path.basename(source_path)
    stem, ext = os.path.splitext(base)
    candidate = os.path.join(dest_dir, base)
    if not os.path.exists(candidate):
        return os.path.abspath(candidate)
    n = 1
    while True:
        candidate = os.path.join(dest_dir, f"{stem} ({n}){ext}")
        if not os.path.exists(candidate):
            return os.path.abspath(candidate)
        n += 1


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
        console.log(f"Failed to load YAML: {exc}")
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

console.log(f"USER_DATA_PATH: {USER_DATA_PATH}")
console.log(f"EXECUTABLE_PATH: {EXECUTABLE_PATH}")
console.log(f"PROCESS_COMMAND_PORT: {PROCESS_COMMAND_PORT}")

_main_window: webview.Window | None = None
_persist_editor = True
_editor_lock = threading.Lock()
_is_maximized = False
_prev_geometry: tuple[int, int, int, int] | None = None
_current_editor_child: subprocess.Popen | None = None
_current_runner_thread: threading.Thread | None = None
_runner_should_stop = threading.Event()
_shutdown_cleanup_started = threading.Event()


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
        console.log(f"Failed to copy default file: {src} -> {dest}: {exc}")


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

    Sends a command to the inner editor over the localhost process-command server.
    '''
    extra_args = extra_args or {}
    cmdId = str(uuid.uuid4())
    projectFolder = os.path.dirname(symphony_file_path)
    projectName = os.path.splitext(os.path.basename(symphony_file_path))[0]

    if command == "open" and symphony_file_path:
        try:
            addRecentlyViewed(symphony_file_path)
        except Exception as exc:  # noqa: BLE001
            console.log(f"Failed to add to recently viewed on open: {exc}")

    payload = {
        "command": command,
        "id": cmdId,
        "args": {
            "project_file_name": projectName,
            "project_folder_path": projectFolder,
            "symphony_data_path": str(USER_DATA_PATH),
            **extra_args,
        },
    }
    console.log(payload)
    response = postProcessCommandPayload(payload)
    console.log(response)
    return response


def postProcessCommandPayload(payload: dict, timeout: float = 15.0) -> dict:
    '''
    fields:
        payload (dict) - process command payload to send
        timeout (float) - HTTP request timeout in seconds
    outputs: dict

    Posts a process command payload to the editor daemon and returns its JSON response.
    '''
    try:
        body = json.dumps(payload).encode("utf-8")
        request = urlrequest.Request(
            PROCESS_COMMAND_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "id": payload.get("id"),
            "message": "ProcessCommandConnectionError",
            "payload": {"error_message": str(exc)},
        }


def waitForProcessCommandServer(timeout: float = 30.0) -> bool:
    '''
    fields:
        timeout (float) - max time to wait in seconds
    outputs: bool

    Waits for the editor daemon's process command server to accept requests.
    '''
    startedAt = time.time()
    while time.time() - startedAt < timeout:
        try:
            with urlrequest.urlopen(PROCESS_COMMAND_HEALTH_URL, timeout=0.5) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data.get("status") == "success":
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.1)

    return False


def spawnEditor() -> None:
    '''
    fields: none
    outputs: nothing

    Starts the inner editor process in a monitored runner thread.
    '''
    is_python_script = str(EXECUTABLE_PATH).endswith(".py")
    script_path = str(EXECUTABLE_PATH.resolve())
    source_path = str(INNER_DIST_PATH.resolve())

    if is_python_script:
        cmd_name = "pythonw" if sys.platform == "win32" else "python3"
        args = [cmd_name, "-u", script_path, source_path]
    else:
        args = [script_path, source_path]

    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "env": {
            **os.environ,
            "SYMPHONY_PROCESS_COMMAND_PORT": str(PROCESS_COMMAND_PORT),
        },
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
                console.log(f"Failed to spawn editor: {exc}")
                return

            # Grant the editor process explicit permission to call
            # SetForegroundWindow once. Without this, Windows can refuse the
            # editor's own focus call if the user moved focus elsewhere
            # between PM click and editor display, leaving the pygame
            # window stuck behind PM.
            if sys.platform == "win32":
                try:
                    from ctypes import windll  # local import: Windows-only
                    windll.user32.AllowSetForegroundWindow(child.pid)
                except Exception as exc:  # noqa: BLE001
                    console.log(f"AllowSetForegroundWindow(editor) failed: {exc}")

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
                console.log(f"Editor process crashed with code {code}.")
            else:
                console.log("Editor process exited.")
            if _runner_should_stop.is_set() or not _persist_editor:
                console.log("Runner exiting.")
                return
            console.log("Restarting...")

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
        # Cooperative shutdown through the localhost command server first.
        try:
            postProcessCommandPayload({"command": "kill", "id": str(uuid.uuid4()), "args": {}}, timeout=2.0)
        except Exception as exc:  # noqa: BLE001
            console.log(f"kill request failed: {exc}")
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
                serverReady = waitForProcessCommandServer()
                return {
                    "success": serverReady,
                    "message": "Editor already running" if serverReady else "Editor running, but command server did not become ready",
                }
            stopEditor()
            spawnEditor()
            serverReady = waitForProcessCommandServer()
            return {
                "success": serverReady,
                "message": "Editor daemon started" if serverReady else "Editor daemon started, but command server did not become ready",
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# JS-API surface
# ---------------------------------------------------------------------------


class Api:
    """All methods here are callable from JS as ``window.pywebview.api.<name>``.

    The shim in ``preload.js`` re-exports each one under the
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
        # area, so ShowWindow can keep the standard Aero animation. On mac the
        # same call routes through NSWindow.zoom_, which already respects the
        # screen's visibleFrame (menu bar + dock excluded).
        if sys.platform in ("win32", "darwin"):
            try:
                maximized = winman.toggle_native_maximize(_main_window)
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
                console.log(f"maximize failed: {exc}")
                return
        # Linux / unknown-platform fallback
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
        requestAppQuit()

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
        return bool(winman.start_resize(_main_window, edge))

    def beginManualWindowResize(self, edge: str, screen_x: int, screen_y: int) -> bool:
        '''
        fields:
            edge (string) - Resize edge or corner name.
            screen_x (number) - Mouse screen X at drag start.
            screen_y (number) - Mouse screen Y at drag start.
        outputs: boolean

        Captures initial geometry for JS-driven resize handles.
        '''
        return bool(winman.begin_manual_resize(_main_window, edge, screen_x, screen_y))

    def updateManualWindowResize(self, screen_x: int, screen_y: int) -> bool:
        '''
        fields:
            screen_x (number) - Current mouse screen X.
            screen_y (number) - Current mouse screen Y.
        outputs: boolean

        Applies a JS-driven resize update.
        '''
        return bool(winman.update_manual_resize(_main_window, screen_x, screen_y))

    def endManualWindowResize(self) -> None:
        '''
        fields: none
        outputs: nothing

        Clears JS-driven resize state.
        '''
        winman.end_manual_resize()

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
            console.log(f"openExternal failed: {exc}")

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
            console.log(f"openFileLocation failed: {exc}")
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
            console.log(f"[move-file-raw] source buffer bytes={len(buf)}")
            with open(dest_path, "wb") as f:
                f.write(buf)
            dest_size = os.path.getsize(dest_path)
            console.log(f"[move-file-raw] dest file bytes={dest_size}")
            console.log(f"[move-file-raw] originalFilePath={original_file_path or 'N/A'}")
            deleted_original = False
            if original_file_path:
                if os.path.abspath(original_file_path) == os.path.abspath(dest_path):
                    console.log("[move-file-raw] Source and destination are the same path; skipping delete.")
                    return {"success": True, "deletedOriginal": False}
                try:
                    src_size = os.path.getsize(original_file_path)
                except Exception:
                    src_size = -1
                same_size = src_size == dest_size
                console.log(f"[move-file-raw] sizeEqual={same_size}")
                if same_size:
                    res = deleteFile(original_file_path)
                    if not res.get("success"):
                        console.log(f"[move-file-raw] delete failed: {res.get('error')}")
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
            console.log(f"Error reading user settings: {exc}")
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

    # ---- pending external file open --------------------------------------
    def getPendingOpenFile(self) -> dict | None:
        '''
        fields: none
        outputs: dict | None

        Returns the .symphony file that the OS asked Symphony to open (via
        file association) along with a ``knownLocation`` registry hit if the
        file's parent folder is one of the user's registered directories.
        Returns ``None`` when no pending open is queued. The pending file is
        cleared on the first read so webview reloads do not replay the flow.

        Shape:
            {
                "path": "C:/.../Foo.symphony",
                "exists": true,
                "knownLocation": {"section": "Projects", "name": "...", "dir": "C:/..."} | null,
            }
        '''
        global _PENDING_OPEN_FILE, _PENDING_OPEN_FILE_IS_TEST_IMPORT
        with _pending_open_file_lock:
            path = _PENDING_OPEN_FILE
            is_test_import = _PENDING_OPEN_FILE_IS_TEST_IMPORT
            _PENDING_OPEN_FILE = None
            _PENDING_OPEN_FILE_IS_TEST_IMPORT = False
        if not path:
            return None
        exists = True if is_test_import else os.path.exists(path)
        known = None if is_test_import else findFileInRegistry(path) if exists else None
        return {
            "path": path.replace("\\", "/"),
            "exists": exists,
            "knownLocation": (
                {
                    "section": known["section"],
                    "name": known["name"],
                    "dir": known["dir"].replace("\\", "/"),
                }
                if known
                else None
            ),
        }

    def copyAndOpenSymphonyFile(self, source_path: str, dest_dir: str) -> dict:
        '''
        fields:
            source_path (string) - .symphony file outside any registered folder
            dest_dir (string) - registered destination folder
        outputs: dict

        Copies ``source_path`` (and any sibling .json metadata) into the
        registered ``dest_dir``, suffixing the filename if a collision exists.
        Refuses to copy into folders that are not currently registered in
        directory.json. Returns ``{"success": True, "path": "..."}`` on
        success; ``{"success": False, "error": "..."}`` otherwise.
        '''
        try:
            if not source_path or not os.path.exists(source_path):
                return {"success": False, "error": "Source file no longer exists."}
            if not source_path.lower().endswith(".symphony"):
                return {"success": False, "error": "Source is not a .symphony file."}
            if not dest_dir or not os.path.isdir(dest_dir):
                return {"success": False, "error": "Destination folder does not exist."}
            if not isDirectoryRegistered(dest_dir):
                return {
                    "success": False,
                    "error": "Destination folder is not registered in Symphony.",
                }

            source_parent = os.path.normcase(os.path.normpath(os.path.dirname(source_path)))
            dest_parent = os.path.normcase(os.path.normpath(dest_dir))
            if source_parent == dest_parent:
                return {
                    "success": True,
                    "path": os.path.abspath(source_path).replace("\\", "/"),
                    "copied": False,
                }

            target = resolveCopyDestination(source_path, dest_dir)
            shutil.copy2(source_path, target)

            sidecar_src = source_path[: -len(".symphony")] + ".json"
            if os.path.exists(sidecar_src):
                sidecar_target = target[: -len(".symphony")] + ".json"
                try:
                    shutil.copy2(sidecar_src, sidecar_target)
                except Exception as exc:  # noqa: BLE001
                    console.log(f"copyAndOpenSymphonyFile: sidecar copy failed: {exc}")

            return {
                "success": True,
                "path": target.replace("\\", "/"),
                "copied": True,
            }
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

    # ---- drag-out --------------------------------------------------------
    def startFileDrag(self, file_path: str) -> dict:
        '''
        fields:
            file_path (string) - absolute file path to drag out to the OS
        outputs: dict

        Schedules a native OS shell drag for the given path on the WebView's
        UI thread (via PostMessageW + a custom WndProc handler on Windows;
        via dispatch-to-main on macOS). Returns immediately; the modal drag
        runs on the UI thread so it shares mouse capture with the WebView's
        in-flight HTML5 drag instead of fighting it.
        '''
        console.log(f"[symphony-drag] Api.startFileDrag invoked: {file_path}")
        if not file_path:
            return {"started": False, "reason": "missing-path"}
        try:
            ok = nativeStartDrag(file_path)
            console.log(f"[symphony-drag] nativeStartDrag posted ok={ok}")
            return {"started": bool(ok)}
        except Exception as exc:  # noqa: BLE001
            console.log(f"[symphony-drag] startFileDrag failed: {exc}")
            return {"started": False, "error": str(exc)}

    def copyPathsInto(self, paths: list[str], destination_dir: str) -> dict:
        '''
        fields:
            paths (list) - absolute source file paths to copy into the folder
            destination_dir (string) - destination folder path
        outputs: dict

        Copies a set of files into a destination folder using shutil.copy2 so
        large drops do not need to round-trip through base64. Filters paths by
        the supported extension set used by the rest of the app.
        '''
        console.log(f"[symphony-drag] Api.copyPathsInto destination={destination_dir} paths={paths}")
        if not destination_dir:
            return {"success": False, "error": "missing-destination"}
        if not isinstance(paths, list):
            return {"success": False, "error": "paths-not-list"}
        try:
            os.makedirs(destination_dir, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

        copied: list[str] = []
        skipped: list[dict] = []
        for source in paths:
            try:
                if not source:
                    continue
                if not os.path.isfile(source):
                    skipped.append({"path": source, "reason": "not-a-file"})
                    continue
                ext = os.path.splitext(source)[1].lower()
                if ext not in VALID_FILE_EXTS:
                    skipped.append({"path": source, "reason": "unsupported-extension"})
                    continue
                dest_path = os.path.join(destination_dir, os.path.basename(source))
                if os.path.abspath(source) == os.path.abspath(dest_path):
                    skipped.append({"path": source, "reason": "same-location"})
                    continue
                shutil.copy2(source, dest_path)
                copied.append(dest_path)
            except Exception as exc:  # noqa: BLE001
                skipped.append({"path": source, "reason": str(exc)})
        return {
            "success": len(copied) > 0 or len(skipped) == 0,
            "copied": copied,
            "skipped": skipped,
        }

    # ---- editor daemon ---------------------------------------------------
    def runEditorProgram(self) -> dict:
        '''
        fields: none
        outputs: dict

        Starts the editor daemon through the shared runner helper.
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


def performShutdownCleanup() -> None:
    '''
    fields: none
    outputs: nothing

    Runs the one-time shutdown cleanup shared by native Quit and the custom
    titlebar close button.
    '''
    global _persist_editor
    if _shutdown_cleanup_started.is_set():
        return
    _shutdown_cleanup_started.set()
    _persist_editor = False
    console.log("--> Stopping editor subprocess..")
    try:
        stopEditor()
    except Exception as exc:  # noqa: BLE001
        console.log(f"stopEditor failed: {exc}")


def requestAppQuit() -> None:
    '''
    fields: none
    outputs: nothing

    Starts a full app shutdown from the JS API close button. The pywebview
    bridge can hang if the window is destroyed synchronously while it is waiting
    for this API call to return, so the button returns immediately and a worker
    exits the backend after cleanup. The Rust shell exits when backend stdout
    closes, matching native Quit's process teardown.
    '''
    def shutdownWorker() -> None:
        try:
            performShutdownCleanup()
        finally:
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception:  # noqa: BLE001
                pass
            os._exit(0)

    threading.Thread(
        target=shutdownWorker,
        name="symphony-app-quit",
        daemon=False,
    ).start()


def onClosing() -> bool:
    '''
    fields: none
    outputs: boolean

    Handles window shutdown by stopping the editor process before close completes.
    '''
    performShutdownCleanup()
    return True


READY_MARKER = "__SYMPHONY_READY__"
_ready_marker_emitted = threading.Event()
PROJECT_MANAGER_WIDTH = 1300
PROJECT_MANAGER_HEIGHT = 800
PROJECT_MANAGER_MIN_WIDTH = 800
PROJECT_MANAGER_MIN_HEIGHT = 800
PROJECT_MANAGER_OFFSCREEN_X = -32000
PROJECT_MANAGER_OFFSCREEN_Y = -32000


def emitReadyMarker() -> None:
    '''
    fields: none
    outputs: nothing

    Signals the Tauri splash launcher after the editor can accept commands and
    the hidden Project Manager webview is ready to reveal.
    '''
    if _ready_marker_emitted.is_set():
        return
    console.log(READY_MARKER, flush=True)
    _ready_marker_emitted.set()


def waitForEditorBeforeProjectManager() -> None:
    '''
    fields: none
    outputs: nothing

    Blocks Project Manager webview creation until the editor is responsive.
    '''
    result = runEditorProgram()
    console.log(result)
    while not result.get("success"):
        time.sleep(1.0)
        if editorIsRunning() and waitForProcessCommandServer():
            result = {"success": True, "message": "Editor command server became ready"}
        else:
            result = runEditorProgram()
        console.log(result)


def moveProjectManagerOnscreen() -> None:
    '''
    fields: none
    outputs: nothing

    Moves the preloaded Project Manager from its offscreen load position to the
    center of the current work area.
    '''
    if not _main_window:
        return
    if not winman.center_window(_main_window, PROJECT_MANAGER_WIDTH, PROJECT_MANAGER_HEIGHT):
        work_area = winman.get_work_area()
        if work_area:
            work_x, work_y, work_w, work_h = work_area
            x = work_x + max((work_w - PROJECT_MANAGER_WIDTH) // 2, 0)
            y = work_y + max((work_h - PROJECT_MANAGER_HEIGHT) // 2, 0)
        else:
            x = 100
            y = 100
        try:
            _main_window.move(int(x), int(y))
        except Exception as exc:  # noqa: BLE001
            console.log(f"moveProjectManagerOnscreen failed: {exc}")
    try:
        if sys.platform == "darwin" and _main_window and hasattr(_main_window, "show"):
            _main_window.show()
        winman.focus_main_window(_main_window)
    except Exception as exc:  # noqa: BLE001
        console.log(f"focus Project Manager failed: {exc}")


def emitNativeDrop(paths: list[str], screen_x: int, screen_y: int) -> None:
    '''
    fields:
        paths (list) - absolute file paths read from the OS drop
        screen_x (number) - drop screen X coordinate
        screen_y (number) - drop screen Y coordinate
    outputs: nothing

    Forwards a native OS file drop into the WebView as a custom JS payload.
    '''
    console.log(f"[symphony-drag] emitNativeDrop paths={paths} at ({screen_x},{screen_y})")
    if not _main_window or not paths:
        return
    payload = json.dumps({
        "paths": list(paths),
        "screenX": int(screen_x),
        "screenY": int(screen_y),
    })
    try:
        _main_window.evaluate_js(
            f"window.__symphonyNativeDrop && window.__symphonyNativeDrop({payload})"
        )
    except Exception as exc:  # noqa: BLE001
        console.log(f"[symphony-drag] emitNativeDrop evaluate_js failed: {exc}")


def onLoaded() -> None:
    '''
    fields: none
    outputs: nothing

    Handles webview load completion and starts the editor process when needed.
    '''
    if sys.platform in ("win32", "darwin"):
        winman.install_aero_and_resize(_main_window, lambda: Api().maximize())
    try:
        nativeRegisterDrop(_main_window, emitNativeDrop)
    except Exception as exc:  # noqa: BLE001
        console.log(f"nativeRegisterDrop failed: {exc}")
    moveProjectManagerOnscreen()
    emitReadyMarker()


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

    setAppUserModelId()
    startPmHandoffServer()

    asset_dir = APP_ROOT / "src" / "assets"
    ensureFile(asset_dir / "user-settings.json", USER_SETTINGS_PATH, DEFAULT_SETTINGS)
    ensureFile(
        asset_dir / "directory.json",
        DIRECTORY_PATH,
        {"Projects": [], "Exports": [], "Symphony Auto-Save": []},
    )
    ensureFile(asset_dir / "starred.json", STARRED_PATH, [])
    ensureFile(asset_dir / "recently-viewed.json", RECENTLY_VIEWED_PATH, [])

    waitForEditorBeforeProjectManager()

    api = Api()
    windowOptions = {
        "title": "Symphony",
        "url": resolveUrl(),
        "js_api": api,
        "width": PROJECT_MANAGER_WIDTH,
        "height": PROJECT_MANAGER_HEIGHT,
        "min_size": (PROJECT_MANAGER_MIN_WIDTH, PROJECT_MANAGER_MIN_HEIGHT),
        "frameless": True,
        "easy_drag": False,
    }
    if sys.platform == "darwin":
        # Cocoa reports no active screen for extreme offscreen coordinates,
        # which can crash pywebview during the initial move callback.
        windowOptions["hidden"] = True
    else:
        windowOptions["x"] = PROJECT_MANAGER_OFFSCREEN_X
        windowOptions["y"] = PROJECT_MANAGER_OFFSCREEN_Y

    _main_window = webview.create_window(**windowOptions)
    _main_window.events.maximized += onMaximized
    _main_window.events.restored += onRestored
    _main_window.events.closing += onClosing
    _main_window.events.loaded += onLoaded

    if sys.platform in ("win32", "darwin"):
        def winAeroDeferred():
            '''
            fields: none
            outputs: nothing

            Applies deferred chrome fixes after pywebview finishes initializing.
            On Windows this also performs a 1-px nudge to wake up resize grips;
            mac just runs the install (idempotent with the onLoaded call).
            '''
            if sys.platform == "win32":
                time.sleep(0.8)   # wait for WinForms to finish its own init
            winman.install_aero_and_resize(_main_window, lambda: Api().maximize())
            # Activate resize grips by doing a 1-px nudge through pywebview's
            # own resize path (WinForms UI thread).  This is the same code path
            # maximize takes; our background-thread SetWindowPos alone is not
            # enough because WinForms marshals the actual style commit to the UI
            # thread and we need that commit to happen before grips are live.
            # The nudge is a Win-only ritual; AppKit does not need it.
            if sys.platform != "win32":
                return
            time.sleep(0.05)
            if _main_window:
                try:
                    w = int(_main_window.width)
                    h = int(_main_window.height)
                    _main_window.resize(w + 1, h)
                    time.sleep(0.05)
                    _main_window.resize(w, h)
                except Exception as exc:
                    console.log(f"startup grip nudge failed: {exc}")
        webview.start(debug=not IS_FROZEN, func=winAeroDeferred)
    else:
        webview.start(debug=not IS_FROZEN)


if __name__ == "__main__":
    main()
