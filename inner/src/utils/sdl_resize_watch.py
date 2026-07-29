# Live window-resize notifications for the pygame/SDL2 editor window.
#
# pygame's normal event queue (pygame.event.pump/get) is only drained by our
# own main loop. During a native OS drag-resize, Windows and macOS both run a
# blocking modal loop on the same thread, so our loop never gets a turn until
# the drag ends -- the UI appears frozen mid-drag even though SDL itself is
# notified continuously.
#
# SDL_AddEventWatch registers a C callback that SDL invokes synchronously
# from inside that blocked modal loop, for both platforms, since SDL already
# normalizes the Win32/Cocoa difference internally. Hooking that lets us
# reflow the UI live during the drag instead of only on mouse-up.

from __future__ import annotations

import ctypes
import glob
import os
import sys
import time
from typing import Callable

import pygame

SDL_WINDOWEVENT = 0x200
SDL_WINDOWEVENT_RESIZED = 5

# Minimum seconds between full layout reflows. 0 reflows on every resize
# event, which is the most responsive the drag can be -- SDL only calls the
# watch when an event arrives, so there is no way to reflow more often than
# that. Raise this (e.g. 1/60) to cap the rate if a full reflow proves too
# expensive on slower machines; ticks in between then take the cheap path in
# handleResize() rather than being dropped.
_MIN_INTERVAL_S = 0.0

_sdl = None
_watch_callback = None
_installed = False
_handling_resize = False
_last_handled_at = 0.0
_min_size = None


class _SDL_WindowEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint32),
        ("windowID", ctypes.c_uint32),
        ("event", ctypes.c_uint8),
        ("padding1", ctypes.c_uint8),
        ("padding2", ctypes.c_uint8),
        ("padding3", ctypes.c_uint8),
        ("data1", ctypes.c_int32),
        ("data2", ctypes.c_int32),
    ]


class _SDL_Event(ctypes.Union):
    # SDL_Event is a union of many event structs; we only need to read the
    # leading `type` field and, when it's a window event, `window`. Padding
    # it out to SDL2's real union size (56 bytes) keeps the layout safe even
    # though we only declare one variant.
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("window", _SDL_WindowEvent),
        ("_padding", ctypes.c_uint8 * 56),
    ]


def _load_sdl():
    global _sdl
    if _sdl is not None:
        return _sdl
    try:
        if sys.platform == "win32":
            # pygame already loaded SDL2.dll into this process; this resolves
            # to that same module by name rather than loading a second copy.
            _sdl = ctypes.WinDLL("SDL2.dll")
        else:
            pygame_dir = os.path.dirname(pygame.__file__)
            candidates = glob.glob(os.path.join(pygame_dir, "**", "*SDL2*.dylib"), recursive=True)
            candidates += glob.glob(os.path.join(pygame_dir, "**", "*SDL2*.so*"), recursive=True)
            if not candidates:
                return None
            # dlopen dedups by canonical path, so this attaches to the copy
            # pygame already loaded instead of loading a second instance.
            _sdl = ctypes.CDLL(candidates[0])
        _sdl.SDL_AddEventWatch.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        _sdl.SDL_AddEventWatch.restype = None
        _sdl.SDL_GetWindowFromID.argtypes = [ctypes.c_uint32]
        _sdl.SDL_GetWindowFromID.restype = ctypes.c_void_p
        _sdl.SDL_SetWindowMinimumSize.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        _sdl.SDL_SetWindowMinimumSize.restype = None
    except Exception:
        _sdl = None
    return _sdl


def _current_sdl_window():
    """Resolve the live SDL_Window* for pygame's display window."""
    from pygame._sdl2.video import Window

    sdl = _load_sdl()
    if sdl is None:
        return None, None
    try:
        window_id = Window.from_display_module().id
        return sdl, sdl.SDL_GetWindowFromID(ctypes.c_uint32(window_id))
    except Exception:
        return None, None


def set_minimum_window_size(min_w: int, min_h: int) -> bool:
    """Enforce a hard OS-level floor on the real (native) window size.

    pygame's `pygame._sdl2.video.Window` wrapper doesn't expose SDL's
    SDL_SetWindowMinimumSize, so this calls it directly via ctypes, resolving
    the SDL_Window* from the window ID pygame does expose. Once set, the OS
    itself refuses to let a live drag-resize go below this size.

    Remembers the size so reapply_minimum_window_size() can restore it after
    a set_mode() call.
    """
    global _min_size

    sdl, sdl_window = _current_sdl_window()
    if sdl is None or not sdl_window:
        return False
    try:
        sdl.SDL_SetWindowMinimumSize(sdl_window, int(min_w), int(min_h))
        _min_size = (int(min_w), int(min_h))
        return True
    except Exception:
        return False


def reapply_minimum_window_size() -> bool:
    """Restore the minimum size previously set via set_minimum_window_size().

    pygame.display.set_mode() silently resets the window's minimum size to
    (1, 1) -- verified against pygame 2.6.1 / SDL 2.28.4. Every set_mode()
    call must therefore be followed by this, or the OS will let a live
    drag-resize shrink the window below the minimum. When that happens the
    clamped surface size and the real window size disagree, which renders as
    black frames mid-drag.
    """
    if _min_size is None:
        return False
    sdl, sdl_window = _current_sdl_window()
    if sdl is None or not sdl_window:
        return False
    try:
        sdl.SDL_SetWindowMinimumSize(sdl_window, _min_size[0], _min_size[1])
        return True
    except Exception:
        return False


def install_live_resize_watch(on_resize: Callable[[int, int, bool], None]) -> bool:
    """Register on_resize to fire live during an OS drag-resize.

    on_resize(width, height, full) is called synchronously from SDL's
    event-watch mechanism, potentially from inside the OS's blocking modal
    drag loop, so it must always paint something and flip -- the OS has
    already resized the real window by the time this fires, so skipping the
    call entirely (rather than passing full=False) leaves the newly-exposed
    window area with no valid backbuffer content. `full` tells the caller
    whether it's safe to do the expensive relayout this tick or whether it
    should just repaint cheaply and flip.

    Safe to call more than once; only the first call installs the watch.
    """
    global _watch_callback, _installed

    if _installed:
        return True

    sdl = _load_sdl()
    if sdl is None:
        return False

    SDL_EventFilter = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(_SDL_Event))

    def _on_event(userdata, event_ptr):
        global _handling_resize, _last_handled_at
        try:
            event = event_ptr.contents
            if event.type == SDL_WINDOWEVENT and event.window.event == SDL_WINDOWEVENT_RESIZED:
                if _handling_resize:
                    return 0
                now = time.monotonic()
                full = (now - _last_handled_at) >= _MIN_INTERVAL_S
                _handling_resize = True
                try:
                    on_resize(event.window.data1, event.window.data2, full)
                finally:
                    if full:
                        _last_handled_at = time.monotonic()
                    _handling_resize = False
        except Exception:
            pass
        return 0

    # Keep a reference alive at module scope: SDL holds a raw pointer to this
    # callback, so letting it get garbage-collected would crash the process.
    _watch_callback = SDL_EventFilter(_on_event)
    sdl.SDL_AddEventWatch(_watch_callback, None)
    _installed = True
    return True
