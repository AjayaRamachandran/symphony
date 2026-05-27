# editor/editor_window.py
# Builds the pywebview editor window using the same winman chrome
# patterns as the project manager.
#
# This module owns:
#   * URL resolution for the editor frontend (vite dev or built dist)
#   * winman selection per platform (win64 / macos / null stub)
#   * post-load chrome installation (frameless aero / resize grips)
#   * window-state propagation back to the React stub
###### IMPORT ######

import os
import sys
import threading
import time
from pathlib import Path

###### INTERNAL MODULES ######

from console_controls.console import *

###### CONSTANTS ######

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 800
MIN_WIDTH = 1000
MIN_HEIGHT = 592

DEV_URL_ENV = "SYMPHONY_EDITOR_URL"
DIST_RELATIVE = ("dist", "inner", "src", "gui", "editor.html")
DEV_FALLBACK_URL = "http://localhost:5173/inner/src/gui/editor.html"

###### HELPERS ######

def _repoRoot() -> Path:
    '''
    fields: none
    outputs: Path

    Returns the repository root from the inner editor module path.
    '''
    return Path(__file__).resolve().parents[3]


def _resolveEditorUrl() -> str:
    '''
    fields: none
    outputs: string

    Resolves the URL the editor webview should load. Honors
    SYMPHONY_EDITOR_URL when set, prefers a built dist when frozen,
    and falls back to the vite dev server for in-development runs.
    '''
    override = os.environ.get(DEV_URL_ENV)
    if override:
        return override

    repoRoot = _repoRoot()
    distEditor = repoRoot.joinpath(*DIST_RELATIVE)

    if getattr(sys, "frozen", False):
        if distEditor.exists():
            return str(distEditor.resolve())
        return DEV_FALLBACK_URL

    if os.environ.get("SYMPHONY_DEV", "1") != "0":
        return DEV_FALLBACK_URL

    if distEditor.exists():
        return str(distEditor.resolve())
    return DEV_FALLBACK_URL


def _selectWinman():
    '''
    fields: none
    outputs: module

    Imports and returns the platform winman module. Uses a null stub on
    Linux so callers can use the same call surface unconditionally.
    '''
    repoRoot = _repoRoot()
    repoRootStr = str(repoRoot)
    if repoRootStr not in sys.path:
        sys.path.insert(0, repoRootStr)

    if sys.platform == "win32":
        from winman import win64_winman as winmanModule  # type: ignore
        return winmanModule
    if sys.platform == "darwin":
        from winman import macos_winman as winmanModule  # type: ignore
        return winmanModule

    class _NullWinman:
        def patch_webview_nonclient(self, *a, **kw): return None
        def get_work_area(self, *a, **kw): return None
        def center_window(self, *a, **kw): return False
        def install_aero_and_resize(self, *a, **kw): return None
        def start_resize(self, *a, **kw): return False
        def begin_manual_resize(self, *a, **kw): return False
        def update_manual_resize(self, *a, **kw): return False
        def end_manual_resize(self, *a, **kw): return None
        def toggle_native_maximize(self, *a, **kw): return None
        def focus_main_window(self, *a, **kw): return None

    return _NullWinman()


###### CLASSES ######

class EditorWindowHost:
    '''
    Coordinates the lifetime of the editor pywebview window.

    The inner process creates one EditorWindowHost per session while the
    shared pywebview event loop is already running. The host forwards
    state-change events to the JS stub and ensures the session is closed
    when the window is destroyed.
    '''

    def __init__(self, session, titleText: str):
        '''
        fields:
            session (EditorSession) - active editor session
            titleText (string) - project file title for the window caption
        outputs: nothing
        '''
        self.session = session
        self.titleText = titleText
        self.window = None
        self.winman = _selectWinman()
        self._isMaximized = False
        self._closing = False
        self.closedEvent = threading.Event()

    # ---- creation -------------------------------------------------------

    def createWindow(self, api):
        '''
        fields:
            api (EditorApi) - js_api instance to expose to the frontend
        outputs: webview.Window

        Creates the pywebview window with the editor URL and js_api. Hooks
        events for chrome installation, maximize/restore propagation, and
        cooperative close (final save).
        '''
        try:
            self.winman.patch_webview_nonclient()
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor patch_webview_nonclient failed: {exc}")

        import webview  # local import: pywebview only needed when window opens

        url = _resolveEditorUrl()
        console.log(f"editor webview url: {url}")

        windowOptions = {
            "title": f"{self.titleText} - Symphony",
            "url": url,
            "js_api": api,
            "width": DEFAULT_WIDTH,
            "height": DEFAULT_HEIGHT,
            "min_size": (MIN_WIDTH, MIN_HEIGHT),
            "frameless": True,
            "easy_drag": False,
        }
        if sys.platform == "darwin":
            windowOptions["hidden"] = True

        self.window = webview.create_window(**windowOptions)
        self.window.events.maximized += self._onMaximized
        self.window.events.restored += self._onRestored
        self.window.events.closing += self._onClosing
        if hasattr(self.window.events, "closed"):
            self.window.events.closed += self._onClosed
        self.window.events.loaded += self._onLoaded

        self.session.setStateChangeCallback(self._emitDocumentState)
        return self.window

    def runBlocking(self):
        '''
        fields: none
        outputs: nothing

        Runs the pywebview event loop. Kept for legacy callers; the inner
        editor process now uses one shared event loop for every editor window.
        '''
        import webview  # local import

        debug = not getattr(sys, "frozen", False)
        if sys.platform in ("win32", "darwin"):
            webview.start(debug=debug, func=self._deferredChromeInstall)
        else:
            webview.start(debug=debug)

    def installChromeDeferred(self):
        '''
        fields: none
        outputs: nothing
        '''
        self._deferredChromeInstall()

    # ---- lifecycle hooks ------------------------------------------------

    def _onLoaded(self):
        '''
        fields: none
        outputs: nothing

        Runs on the webview UI thread the first time the React stub mounts.
        Installs winman chrome and pushes the initial document snapshot
        into the frontend.
        '''
        try:
            if sys.platform in ("win32", "darwin"):
                self.winman.install_aero_and_resize(self.window, self._noopMaximize)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor install_aero_and_resize (loaded) failed: {exc}")

        try:
            if sys.platform == "darwin" and hasattr(self.window, "show"):
                self.window.show()
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor mac show failed: {exc}")

        self._centerOnscreen()
        self._focus()
        self._emitDocumentState()

    def _onClosing(self):
        '''
        fields: none
        outputs: nothing

        Pywebview fires this just before the window is destroyed. We
        synchronously persist and stop autosave so the editor session
        can close cleanly afterwards.
        '''
        if self._closing:
            return
        self._closing = True
        try:
            self.session.close()
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor session close failed: {exc}")
        finally:
            self.closedEvent.set()

    def _onClosed(self):
        '''
        fields: none
        outputs: nothing
        '''
        if not self._closing:
            self._onClosing()
        self.closedEvent.set()

    def _onMaximized(self):
        '''
        fields: none
        outputs: nothing
        '''
        self._isMaximized = True
        self._evaluateJs(
            "window.__symphony_emit_window_state && window.__symphony_emit_window_state(true)"
        )

    def _onRestored(self):
        '''
        fields: none
        outputs: nothing
        '''
        self._isMaximized = False
        self._evaluateJs(
            "window.__symphony_emit_window_state && window.__symphony_emit_window_state(false)"
        )

    def _deferredChromeInstall(self):
        '''
        fields: none
        outputs: nothing

        Mirrors the project manager's deferred chrome install. On Windows
        we wait for WinForms to finish initializing before applying the
        non-client subclass; on macOS the install is idempotent with the
        onLoaded call.
        '''
        try:
            if sys.platform == "win32":
                time.sleep(0.8)
            self.winman.install_aero_and_resize(self.window, self._noopMaximize)
            if sys.platform != "win32":
                return
            time.sleep(0.05)
            if self.window:
                try:
                    w = int(self.window.width)
                    h = int(self.window.height)
                    self.window.resize(w + 1, h)
                    time.sleep(0.05)
                    self.window.resize(w, h)
                except Exception as exc:  # noqa: BLE001
                    console.warn(f"editor startup grip nudge failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor deferred chrome install failed: {exc}")

    # ---- helpers --------------------------------------------------------

    def _noopMaximize(self):
        '''
        fields: none
        outputs: nothing

        Placeholder used by ``winman.install_aero_and_resize``; the actual
        toggle goes through the EditorApi.maximize path.
        '''
        try:
            if self.window:
                self.winman.toggle_native_maximize(self.window)
        except Exception:  # noqa: BLE001
            pass

    def _centerOnscreen(self):
        '''
        fields: none
        outputs: nothing
        '''
        if not self.window:
            return
        try:
            if not self.winman.center_window(self.window, DEFAULT_WIDTH, DEFAULT_HEIGHT):
                workArea = self.winman.get_work_area()
                if workArea:
                    workX, workY, workW, workH = workArea
                    x = workX + max(0, (workW - DEFAULT_WIDTH) // 2)
                    y = workY + max(0, (workH - DEFAULT_HEIGHT) // 2)
                else:
                    x, y = 100, 100
                try:
                    self.window.move(int(x), int(y))
                except Exception as exc:  # noqa: BLE001
                    console.warn(f"editor center fallback move failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor center failed: {exc}")

    def _focus(self):
        '''
        fields: none
        outputs: nothing
        '''
        try:
            self.winman.focus_main_window(self.window)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor focus failed: {exc}")

    def _emitDocumentState(self):
        '''
        fields: none
        outputs: nothing

        Sends the latest document snapshot to the React stub via
        ``window.__symphony_editor_state(state)``.
        '''
        if not self.window:
            return
        try:
            import json
            state = self.session.getDocumentState()
            payload = json.dumps(state, default=str)
            self._evaluateJs(
                f"window.__symphony_editor_state && window.__symphony_editor_state({payload})"
            )
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor _emitDocumentState failed: {exc}")

    def _evaluateJs(self, script: str):
        '''
        fields:
            script (string) - JavaScript snippet to execute in the webview
        outputs: nothing
        '''
        if not self.window:
            return
        try:
            self.window.evaluate_js(script)
        except Exception as exc:  # noqa: BLE001
            console.warn(f"editor evaluate_js failed: {exc}")
