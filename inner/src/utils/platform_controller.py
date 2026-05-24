# utils/platform_controller.py
# module for handling platform-specific functionality.
###### INTERNAL MODULES ######

from console_controls.console import *

###### EXTERNAL MODULES ######

import sys
import pygame

###### FUNCTIONS ######

def getPlatformNameAndMeta():
    if sys.platform.startswith("win"):
        console.message("Running on Windows")
        platform = 'windows'
        CMD_KEY = pygame.K_LCTRL
    elif sys.platform == "darwin":
        console.message("Running on macOS")
        platform = 'mac'
        CMD_KEY = pygame.K_LMETA
    elif sys.platform.startswith("linux"):
        console.message("Running on Linux")
        platform = 'linux'
        CMD_KEY = pygame.K_LCTRL
    else:
        console.warn(f"Running on unknown platform: {sys.platform}")
        platform = 'unknown'
        CMD_KEY = pygame.K_LCTRL

    try:
        from ctypes import windll
        # Canonical Symphony AppUserModelID. Must match Tauri's ``identifier``
        # in ``src-tauri/tauri.conf.json``, the Rust launcher
        # (``src-tauri/src/main.rs``), and the backend (``main.py``). The
        # installer stamps this same ID onto the Symphony Start Menu / Desktop
        # shortcuts, so pinning the editor window resolves back to the
        # installed Symphony app instead of registering a separate pin for the
        # inner editor binary.
        myappid = 'com.ajayarsymphony.desktop'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        console.warn('Error importing windll or setting Unique AppID. You might be gui_running on a non-Windows platform.')
        pass # Not on Windows or ctypes is not available

    return platform, CMD_KEY


def bringEditorWindowToFront():
    '''
    fields: none
    outputs: nothing

    Surfaces the editor's pygame window to the foreground so it doesn't get
    lost behind the project manager when a piece is opened. Call this after
    pygame.display.set_mode + flip on the open path. No-op on Linux and on
    any failure path; this is purely a UX nicety.

    On Windows this also performs the AttachThreadInput trick so
    SetForegroundWindow succeeds even when this process did not strictly
    "own" the foreground at the moment of the call. The PM also calls
    AllowSetForegroundWindow(<editor pid>) just after spawning us, which is
    the more reliable path on modern Windows.
    '''
    try:
        if sys.platform == "win32":
            _bringToFrontWindows()
        elif sys.platform == "darwin":
            _bringToFrontMac()
    except Exception as exc:  # noqa: BLE001
        console.warn(f"bringEditorWindowToFront failed: {exc}")


def _bringToFrontWindows():
    import ctypes
    from ctypes import wintypes as wt

    info = pygame.display.get_wm_info()
    hwnd = int(info.get("window", 0))
    if not hwnd:
        return

    user32 = ctypes.WinDLL("user32")
    kernel32 = ctypes.WinDLL("kernel32")
    user32.IsIconic.restype = ctypes.c_bool
    user32.IsIconic.argtypes = [wt.HWND]
    user32.ShowWindow.restype = ctypes.c_bool
    user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
    user32.SetForegroundWindow.restype = ctypes.c_bool
    user32.SetForegroundWindow.argtypes = [wt.HWND]
    user32.BringWindowToTop.restype = ctypes.c_bool
    user32.BringWindowToTop.argtypes = [wt.HWND]
    user32.GetForegroundWindow.restype = wt.HWND
    user32.GetWindowThreadProcessId.restype = wt.DWORD
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    user32.AttachThreadInput.restype = ctypes.c_bool
    user32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, ctypes.c_bool]
    kernel32.GetCurrentThreadId.restype = wt.DWORD

    SW_RESTORE = 9
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)

    fg_hwnd = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
    cur_thread = kernel32.GetCurrentThreadId()
    attached = False
    try:
        if fg_thread and fg_thread != cur_thread:
            attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(cur_thread, fg_thread, False)


def _bringToFrontMac():
    try:
        from AppKit import NSApp  # type: ignore[import]
    except Exception as exc:  # noqa: BLE001
        console.warn(f"_bringToFrontMac: PyObjC import failed: {exc}")
        return
    NSApp.activateIgnoringOtherApps_(True)


def setDockIconVisible(visible: bool):
    '''
    fields:
        visible (boolean) - whether the macOS app should appear in the Dock
    outputs: nothing

    Toggles the process activation policy on macOS. This lets the persistent
    editor daemon hide its Dock icon after the SDL window is hidden without
    destroying the Cocoa window, which has historically caused hangs.
    '''
    if sys.platform != "darwin":
        return
    try:
        from AppKit import (  # type: ignore[import]
            NSApp,
            NSApplicationActivationPolicyAccessory,
            NSApplicationActivationPolicyRegular,
        )
    except Exception as exc:  # noqa: BLE001
        console.warn(f"setDockIconVisible: PyObjC import failed: {exc}")
        return

    try:
        policy = (
            NSApplicationActivationPolicyRegular
            if visible
            else NSApplicationActivationPolicyAccessory
        )
        NSApp.setActivationPolicy_(policy)
    except Exception as exc:  # noqa: BLE001
        console.warn(f"setDockIconVisible failed: {exc}")
