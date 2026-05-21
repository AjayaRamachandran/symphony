# winman/macos_winman.py
# macOS PyObjC peer of winman/win64_winman.py.
#
# Exposes the same function names as winman.win64_winman so main.py can pick a backend
# at import time and keep its `winman.<fn>(...)` call sites unchanged. Every
# function early-returns on non-darwin platforms so accidental imports are
# harmless.

from __future__ import annotations
import sys

_manual_resize_start: dict | None = None
_install_done: bool = False


def patch_webview_nonclient() -> None:
    """No-op on macOS. The WebView2 non-client-region quirk is Windows-only."""
    return


def get_work_area() -> tuple[int, int, int, int] | None:
    """Return the primary screen's visible frame as (x, y, w, h) in top-left coords."""
    if sys.platform != "darwin":
        return None
    try:
        from AppKit import NSScreen  # type: ignore[import]

        screens = NSScreen.screens()
        if not screens:
            return None
        primary = screens[0]
        primary_h = float(primary.frame().size.height)
        vf = primary.visibleFrame()
        # Cocoa origin is bottom-left; flip to top-left to match winman.win64_winman.
        x = int(vf.origin.x)
        y = int(primary_h - vf.origin.y - vf.size.height)
        return (x, y, int(vf.size.width), int(vf.size.height))
    except Exception as exc:
        print(f"get_work_area failed: {exc}")
        return None


def _get_nswindow(main_window):
    """Resolve the underlying NSWindow from a pywebview Window."""
    if sys.platform != "darwin" or not main_window:
        return None
    try:
        from AppKit import NSApp, NSWindow  # type: ignore[import]
    except Exception as exc:
        print(f"mac_w: PyObjC import failed: {exc}")
        return None

    native = getattr(main_window, "native", None)
    if native is not None:
        if isinstance(native, NSWindow):
            return native
        # pywebview cocoa exposes a `.window` attribute or selector that returns
        # the NSWindow when BrowserView is not itself the window.
        win = getattr(native, "window", None)
        if callable(win):
            try:
                w = win()
                if isinstance(w, NSWindow):
                    return w
            except Exception:
                pass
        elif isinstance(win, NSWindow):
            return win

    title = getattr(main_window, "title", "Symphony")
    try:
        for w in NSApp.windows():
            if str(w.title()) == title:
                return w
    except Exception as exc:
        print(f"mac_w: NSApp.windows fallback failed: {exc}")
    return None


def _run_on_main(callable_, *args) -> None:
    """Marshal a callable onto the AppKit main thread."""
    try:
        from PyObjCTools.AppHelper import callAfter  # type: ignore[import]

        callAfter(callable_, *args)
    except Exception:
        # Best-effort direct call; pywebview's API thread is usually fine for
        # NSWindow geometry calls during a drag.
        try:
            callable_(*args)
        except Exception as exc:
            print(f"mac_w: main-thread dispatch fallback failed: {exc}")


def start_file_drag(file_path: str) -> bool:
    """Placeholder. Cross-platform NSDraggingSession drag-out lives elsewhere."""
    return False


def start_resize(main_window, edge: str) -> bool:
    """Cocoa has no public API to enter the system resize loop.

    Returning False causes the JS shim (preload.js) to fall
    through to the manual begin/update/end path, which is the supported
    mac codepath.
    """
    return False


def begin_manual_resize(main_window, edge: str, screen_x: int, screen_y: int) -> bool:
    """Capture initial geometry so update_manual_resize can do delta math."""
    global _manual_resize_start
    if sys.platform != "darwin" or not main_window:
        return False
    if edge not in {
        "left", "right", "top", "bottom",
        "top-left", "top-right", "bottom-left", "bottom-right",
    }:
        return False
    try:
        nsw = _get_nswindow(main_window)
        if nsw is None:
            print("begin_manual_resize: could not obtain NSWindow")
            return False
        frame = nsw.frame()
        min_w, min_h = getattr(main_window, "min_size", (800, 800)) or (800, 800)
        _manual_resize_start = {
            "edge": edge,
            "nswindow": nsw,
            "screen_x": int(screen_x),
            "screen_y": int(screen_y),
            "x": float(frame.origin.x),
            "y": float(frame.origin.y),
            "width": float(frame.size.width),
            "height": float(frame.size.height),
            "min_width": float(min_w),
            "min_height": float(min_h),
        }
        return True
    except Exception as exc:
        print(f"begin_manual_resize failed: {exc}")
        _manual_resize_start = None
        return False


def update_manual_resize(main_window, screen_x: int, screen_y: int) -> bool:
    """Apply JS-driven resize updates while dragging a custom edge handle."""
    if sys.platform != "darwin" or not main_window or not _manual_resize_start:
        return False
    try:
        from AppKit import NSMakeRect  # type: ignore[import]

        start = _manual_resize_start
        edge = str(start["edge"])
        nsw = start["nswindow"]
        min_w = float(start["min_width"])
        min_h = float(start["min_height"])
        start_x = float(start["x"])
        start_y = float(start["y"])
        start_w = float(start["width"])
        start_h = float(start["height"])

        # JS screenX/Y are CSS pixels from the top-left; in WKWebView those map
        # 1:1 to Cocoa points regardless of Retina scaling.
        dx = float(screen_x) - float(start["screen_x"])
        dy = float(screen_y) - float(start["screen_y"])

        new_x = start_x
        new_y = start_y
        new_w = start_w
        new_h = start_h

        if "left" in edge:
            dx_clamped = min(dx, start_w - min_w)
            new_x = start_x + dx_clamped
            new_w = start_w - dx_clamped
        elif "right" in edge:
            new_w = max(min_w, start_w + dx)

        # Cocoa frame origin is bottom-left. Dragging the top edge down
        # (dy > 0 in JS) shrinks height while origin.y stays put; dragging the
        # bottom edge down grows height and lowers origin.y by the same amount.
        if "top" in edge:
            dy_clamped = min(dy, start_h - min_h)
            new_h = start_h - dy_clamped
        elif "bottom" in edge:
            dy_clamped = max(dy, min_h - start_h)
            new_y = start_y - dy_clamped
            new_h = start_h + dy_clamped

        rect = NSMakeRect(new_x, new_y, new_w, new_h)
        _run_on_main(nsw.setFrame_display_, rect, True)
        return True
    except Exception as exc:
        print(f"update_manual_resize failed: {exc}")
        return False


def end_manual_resize() -> None:
    """Clear JS-driven resize state."""
    global _manual_resize_start
    _manual_resize_start = None


def toggle_native_maximize(main_window) -> bool | None:
    """Toggle NSWindow.zoom_ (green-button behavior, respects visibleFrame)."""
    if sys.platform != "darwin" or not main_window:
        return None
    try:
        nsw = _get_nswindow(main_window)
        if nsw is None:
            print("toggle_native_maximize: could not obtain NSWindow")
            return None
        was_zoomed = bool(nsw.isZoomed())
        _run_on_main(nsw.zoom_, None)
        # zoom_ is async via callAfter, so report the *new* desired state to
        # callers that drive maximize/restore event emission.
        return not was_zoomed
    except Exception as exc:
        print(f"toggle_native_maximize failed: {exc}")
        return None


def install_aero_and_resize(main_window, on_maximize) -> None:
    """Apply the minimum NSWindow tuning a frameless pywebview window needs.

    Mac analog of the WndProc/DWM setup in winman.win64_winman:
      Style     Adds NSWindowStyleMaskResizable so AppKit still recognizes
                edge resize cursors even on a borderless window.
      Min size  setContentMinSize_ mirrors win32 WM_GETMINMAXINFO clamping.
      Drag      setMovableByWindowBackground:NO because the React titlebar
                already owns drag via .pywebview-drag-region.
      Shadow    NSWindow.hasShadow defaults to YES; asserted explicitly.
      Zoom      Handled by NSWindow.zoom_; nothing to install here. The
                on_maximize callback is unused on mac.
    """
    global _install_done
    if sys.platform != "darwin" or not main_window or _install_done:
        return
    try:
        from AppKit import (  # type: ignore[import]
            NSMakeSize,
            NSWindowStyleMaskResizable,
        )

        nsw = _get_nswindow(main_window)
        if nsw is None:
            print("install_aero_and_resize: could not obtain NSWindow — aborting")
            return

        min_w, min_h = getattr(main_window, "min_size", (800, 800)) or (800, 800)
        min_size = NSMakeSize(float(min_w), float(min_h))

        def _apply():
            try:
                nsw.setStyleMask_(nsw.styleMask() | NSWindowStyleMaskResizable)
                nsw.setMovableByWindowBackground_(False)
                nsw.setHasShadow_(True)
                nsw.setContentMinSize_(min_size)
            except Exception as exc:
                print(f"install_aero_and_resize apply failed: {exc}")

        _run_on_main(_apply)
        _install_done = True
        print("install_aero_and_resize: mac NSWindow tuning applied")
    except Exception as exc:
        print(f"install_aero_and_resize failed: {exc}")


def focus_main_window(main_window) -> bool:
    """Activate the Symphony app and bring its main window to the front.

    Mac analog of winman.win64_winman.focus_main_window; used by the
    second-instance handoff so a duplicate Symphony launch surfaces the
    running PM window instead of spawning a second backend.
    """
    if sys.platform != "darwin" or not main_window:
        return False
    try:
        from AppKit import NSApp  # type: ignore[import]
    except Exception as exc:
        print(f"focus_main_window: PyObjC import failed: {exc}")
        return False

    nsw = _get_nswindow(main_window)

    def _activate():
        try:
            NSApp.activateIgnoringOtherApps_(True)
            if nsw is not None:
                if nsw.isMiniaturized():
                    nsw.deminiaturize_(None)
                nsw.makeKeyAndOrderFront_(None)
        except Exception as exc:
            print(f"focus_main_window: activate failed: {exc}")

    _run_on_main(_activate)
    return True
