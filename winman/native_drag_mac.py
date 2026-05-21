# winman/native_drag_mac.py
# macOS-side equivalents of the Windows drag-source / drop-target helpers in
# winman/win64_winman.py. The pywebview Cocoa backend exposes the WKWebView via
# ``window.native``; we reach the underlying view and use AppKit drag APIs
# directly. All AppKit calls must run on the main thread, so helpers below
# marshal through NSOperationQueue.mainQueue when invoked from a worker thread.
#
# Surface mirrors winman.win64_winman:
#   startFileDrag(file_paths) -> bool
#   registerDropTarget(window, on_paths) -> bool
#
# Both are no-ops on non-darwin so callers do not need to guard at the call
# site; main.py's nativeStartDrag / nativeRegisterDrop facade still picks the
# right backend per sys.platform.

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Iterable

INNER_SRC_PATH = Path(__file__).resolve().parents[1] / "inner" / "src"
if str(INNER_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(INNER_SRC_PATH))
from console_controls.console import console

_drag_refs: list = []   # keep PyObjC drag-source instances alive across sessions
_drop_refs: list = []   # keep drop-target swizzle / handler refs alive
_drop_target_installed = False
_SymphonyDragSource = None  # type: ignore[assignment]


def _coerceFilePaths(file_paths) -> list[str]:
    '''
    fields:
        file_paths (string | iterable) - one or more file paths
    outputs: list

    Normalizes input into a list of absolute file paths that exist on disk.
    '''
    if not file_paths:
        return []
    if isinstance(file_paths, (str, bytes, os.PathLike)):
        candidates: Iterable = [file_paths]
    else:
        candidates = file_paths
    resolved: list[str] = []
    for entry in candidates:
        if not entry:
            continue
        absolute = os.path.abspath(str(entry))
        if not os.path.isfile(absolute):
            console.log(f"native_drag_mac: file does not exist: {absolute}")
            continue
        resolved.append(absolute)
    return resolved


def _runOnMain(fn: Callable[[], None]) -> None:
    '''
    fields:
        fn (callable) - zero-argument callable to dispatch onto the AppKit main thread
    outputs: nothing

    Schedules a callable on the AppKit main thread; runs immediately when
    already on the main thread.
    '''
    try:
        from Foundation import NSThread, NSOperationQueue
    except Exception as exc:  # noqa: BLE001
        console.log(f"native_drag_mac main-thread dispatch unavailable: {exc}")
        fn()
        return
    if NSThread.isMainThread():
        fn()
        return
    NSOperationQueue.mainQueue().addOperationWithBlock_(fn)


def startFileDrag(file_paths) -> bool:
    '''
    fields:
        file_paths (string | iterable) - one or more absolute paths
    outputs: boolean

    Begins a Cocoa drag session on the WKWebView so external apps receive a
    real NSPasteboardTypeFileURL payload. Returns True if the session was
    scheduled to start; the actual dragging session runs asynchronously on the
    main thread.
    '''
    if sys.platform != "darwin":
        return False
    paths = _coerceFilePaths(file_paths)
    if not paths:
        return False

    main_window = _resolveMainWindow()
    if main_window is None:
        console.log("native_drag_mac: no active pywebview window")
        return False

    def _begin() -> None:
        '''
        fields: none
        outputs: nothing

        Constructs the dragging items on the AppKit main thread and starts the session.
        '''
        try:
            _beginDragSession(main_window, paths)
        except Exception as exc:  # noqa: BLE001
            console.log(f"native_drag_mac startFileDrag failed: {exc}")

    _runOnMain(_begin)
    return True


def registerDropTarget(window, on_paths) -> bool:
    '''
    fields:
        window (Window) - active pywebview window
        on_paths (callable) - callback invoked with (paths, screenX, screenY)
    outputs: boolean

    Currently a deliberate no-op on macOS: WKWebView already accepts external
    file drops through its built-in dragging destination and surfaces them in
    HTML5 ``dataTransfer.files``, which the React layer handles via
    ``moveFileRaw``. Method-swizzling WKWebView's drop selectors from PyObjC
    is fragile and risks destabilizing the WebKit subsystem, so we keep the
    macOS native drop-in path off until a stable hook is needed (e.g. for
    very large multi-gigabyte drops where base64 round-tripping becomes a
    bottleneck). Returning False signals the facade to fall back to HTML5.
    '''
    return False


# ---------------------------------------------------------------------------
# Private helpers (only imported / executed on darwin to avoid side effects)
# ---------------------------------------------------------------------------


def _resolveMainWindow():
    '''
    fields: none
    outputs: pywebview Window | None

    Returns the active pywebview window or None when the bridge is not loaded.
    '''
    try:
        import webview  # type: ignore[import]
    except Exception:  # noqa: BLE001
        return None
    windows = getattr(webview, "windows", None) or []
    return windows[0] if windows else None


def _resolveWebView(main_window):
    '''
    fields:
        main_window (Window) - pywebview window wrapper
    outputs: WKWebView | None

    Resolves the underlying WKWebView instance from the pywebview Cocoa backend.
    '''
    native = getattr(main_window, "native", None)
    if native is None:
        return None
    # pywebview's cocoa backend stores the WKWebView either directly on
    # ``main_window.native`` or as a child attribute; check both.
    candidate = native
    webkit = getattr(native, "webkit", None)
    if webkit is not None:
        candidate = webkit
    return candidate


def _resolveDragEvent(view):
    '''
    fields:
        view (NSView) - drag source view used to synthesize a fallback event
    outputs: NSEvent | None

    Returns a usable NSEvent for beginDraggingSessionWithItems_event_source_,
    preferring the AppKit current event and synthesizing a left-button-dragged
    event at the current mouse location when the original event has already
    been retired (the JS-API dispatch is asynchronous on macOS, so the
    originating mouseDown is sometimes no longer the current event by the
    time Python runs).
    '''
    from AppKit import NSApp, NSEvent, NSEventTypeLeftMouseDragged

    event = NSApp.currentEvent() if NSApp is not None else None
    if event is not None:
        return event
    try:
        window = view.window() if view is not None else None
        if window is None:
            return None
        screen_loc = NSEvent.mouseLocation()
        window_loc = window.convertPointFromScreen_(screen_loc)
        return NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
            NSEventTypeLeftMouseDragged,
            window_loc,
            0,
            0.0,
            window.windowNumber(),
            None,
            0,
            1,
            1.0,
        )
    except Exception as exc:  # noqa: BLE001
        console.log(f"native_drag_mac _resolveDragEvent failed: {exc}")
        return None


def _beginDragSession(main_window, paths: list[str]) -> None:
    '''
    fields:
        main_window (Window) - pywebview window wrapper
        paths (list) - absolute file paths to include in the drag pasteboard
    outputs: nothing

    Builds NSDraggingItem entries for each path and starts a dragging session
    rooted on the WKWebView using the active mouseDown event.
    '''
    from AppKit import (
        NSDraggingItem,
        NSPasteboardItem,
        NSPasteboardTypeFileURL,
        NSWorkspace,
        NSImage,
    )
    from Foundation import NSURL, NSPoint, NSRect, NSSize

    view = _resolveWebView(main_window)
    if view is None:
        console.log("native_drag_mac: no WKWebView resolved")
        return

    event = _resolveDragEvent(view)
    if event is None:
        console.log("native_drag_mac: no NSEvent available for drag session")
        return

    if _SymphonyDragSource is None:
        console.log("native_drag_mac: drag source class unavailable")
        return

    workspace = NSWorkspace.sharedWorkspace()
    icon_size = NSSize(64.0, 64.0)
    cursor_in_view = view.convertPoint_fromView_(event.locationInWindow(), None)
    base_origin = NSPoint(
        cursor_in_view.x - icon_size.width / 2.0,
        cursor_in_view.y - icon_size.height / 2.0,
    )

    items = []
    for index, path in enumerate(paths):
        url = NSURL.fileURLWithPath_(path)
        pasteboard_item = NSPasteboardItem.alloc().init()
        pasteboard_item.setString_forType_(url.absoluteString(), NSPasteboardTypeFileURL)
        item = NSDraggingItem.alloc().initWithPasteboardWriter_(pasteboard_item)
        icon = workspace.iconForFile_(path) if os.path.isfile(path) else None
        if icon is None:
            icon = NSImage.alloc().initWithSize_(icon_size)
        offset = NSPoint(
            base_origin.x + index * 6.0,
            base_origin.y - index * 6.0,
        )
        item.setDraggingFrame_contents_(NSRect(offset, icon_size), icon)
        items.append(item)

    source = _SymphonyDragSource.alloc().init()
    _drag_refs.append(source)
    try:
        view.beginDraggingSessionWithItems_event_source_(items, event, source)
    except Exception as exc:  # noqa: BLE001
        console.log(f"native_drag_mac beginDraggingSession failed: {exc}")


def _defineDragSourceClass():
    '''
    fields: none
    outputs: NSObject subclass

    Declares the NSDraggingSource subclass that opts every dragging session
    into Copy semantics so external receivers (Finder, Mail, browsers) accept
    the drop.
    '''
    from AppKit import NSObject, NSDragOperationCopy

    class _Source(NSObject):
        def draggingSession_sourceOperationMaskForDraggingContext_(self, _session, _context):
            '''
            fields:
                _session (NSDraggingSession) - active dragging session
                _context (NSDraggingContext) - whether the drop target is in-app or external
            outputs: integer

            Returns Copy as the supported operation mask for every drag context.
            '''
            return NSDragOperationCopy

    return _Source


if sys.platform == "darwin":
    try:
        _SymphonyDragSource = _defineDragSourceClass()
    except Exception as exc:  # noqa: BLE001
        console.log(f"native_drag_mac: failed to define drag source class: {exc}")
        _SymphonyDragSource = None  # type: ignore[assignment]
