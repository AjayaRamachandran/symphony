# win_c.man.py
# Windows ctypes, WndProc, and Aero handlers for the frameless Symphony window.

from __future__ import annotations
import sys
import threading

TITLE_BAR_H = 30   # must match title-bar.css: .titlebar { height: 30px }
BUTTON_W    = 108  # 3 × 36 px window-controls buttons
RESIZE_HANDLE_W = 18  # invisible resize handle width in screen pixels
WINDOW_BORDER_COLOR = 0x004A515B  # COLORREF for a subtle visible DWM border

_win_hook_refs: list = []       # prevent GC of ctypes WndProc callbacks
_win_proc_installed: bool = False
_win_child_proc_installed: set[int] = set()


def patch_webview_nonclient() -> None:
    """Patch WebView2's on_webview_ready to enable non-client region support."""
    if sys.platform != "win32":
        return
    try:
        from webview.platforms import edgechromium as _ec  # type: ignore[import]
        _orig = _ec.EdgeChrome.on_webview_ready

        def _patched(self, sender, args):  # type: ignore[misc]
            _orig(self, sender, args)
            if args.IsSuccess:
                try:
                    sender.CoreWebView2.Settings.IsNonClientRegionSupportEnabled = True
                except AttributeError:
                    pass  # WebView2 SDK < 1.0.2357

        _ec.EdgeChrome.on_webview_ready = _patched
    except Exception as exc:
        print(f"webview nonclient-region patch skipped: {exc}")


def get_work_area() -> tuple[int, int, int, int] | None:
    """Return (x, y, width, height) of the primary monitor's work area, or None."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left",   ctypes.c_long),
                ("top",    ctypes.c_long),
                ("right",  ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        SPI_GETWORKAREA = 0x0030
        rect = RECT()
        if not ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
            return None
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    except Exception as exc:
        print(f"get_work_area failed: {exc}")
        return None


def install_aero_and_resize(main_window, on_maximize) -> None:
    """Enable native resize borders, Aero drop shadow, and Aero Snap.

    Design:
      Style        WS_THICKFRAME for resize grips; WS_CAPTION explicitly
                   REMOVED so DWM does not draw a title-bar area during
                   Aero Snap animations (the white-bar bug).
      WM_NCCALCSIZE → 0   Collapses visible NC area; WS_THICKFRAME still
                          provides invisible resize grips at window edges.
      WM_NCHITTEST        Returns HTCAPTION for the title-bar drag strip so
                          the OS owns native drag and Aero Snap.  The button
                          zone (right BUTTON_W px) returns HTCLIENT so
                          WebView2 delivers those clicks to React normally.
                          Window edges return the appropriate resize codes.
      WM_NCACTIVATE       Forwarded with lParam=-1 to suppress NC repaint flash.
      WM_NCLBUTTONDBLCLK  On HTCAPTION, calls on_maximize() so the window
                          respects the work area instead of going over the taskbar.
      All other messages  Forwarded to the original WinForms WndProc.
    """
    global _win_proc_installed
    if sys.platform != "win32" or not main_window:
        return

    import ctypes
    import ctypes.wintypes as wt

    # Private WinDLL instance so our argtypes don't pollute ctypes.windll.user32
    # (pywebview calls SetWindowPos with None args for SWP_NOSIZE).
    _u32 = ctypes.WinDLL('user32')
    dwm  = ctypes.windll.dwmapi

    # --- get HWND from pywebview's native WinForms Form ----------------------
    hwnd: int = 0
    native = getattr(main_window, "native", None)
    if native is not None:
        try:
            hwnd = native.Handle.ToInt32()
        except Exception as exc:
            print(f"install_aero_and_resize: Handle.ToInt32() failed: {exc}")
    if not hwnd:
        hwnd = ctypes.windll.user32.FindWindowW(None, getattr(main_window, "title", "Symphony"))
    if not hwnd:
        print("install_aero_and_resize: could not obtain HWND — aborting")
        return

    print(f"install_aero_and_resize: HWND={hwnd:#010x}")

    # --- Win32 constants -----------------------------------------------------
    GWL_STYLE      = -16
    GWLP_WNDPROC   = -4
    WS_THICKFRAME  = 0x00040000
    WS_CAPTION     = 0x00C00000  # must be REMOVED — present = white bar on snap
    WS_SYSMENU     = 0x00080000
    WS_MAXIMIZEBOX = 0x00010000
    WS_MINIMIZEBOX = 0x00020000
    SWP_FRAMECHANGED = 0x0020
    SWP_NOACTIVATE   = 0x0010
    SWP_NOZORDER     = 0x0004
    SWP_NOSIZE       = 0x0001
    SWP_NOMOVE       = 0x0002

    WM_NCCALCSIZE      = 0x0083
    WM_NCHITTEST       = 0x0084
    WM_NCACTIVATE      = 0x0086
    WM_NCLBUTTONDOWN   = 0x00A1
    WM_NCLBUTTONDBLCLK = 0x00A3

    HTCLIENT      = 1
    HTCAPTION     = 2
    HTLEFT        = 10
    HTRIGHT       = 11
    HTTOP         = 12
    HTTOPLEFT     = 13
    HTTOPRIGHT    = 14
    HTBOTTOM      = 15
    HTBOTTOMLEFT  = 16
    HTBOTTOMRIGHT = 17
    HTTRANSPARENT = -1

    RESIZE_HT = {HTLEFT, HTRIGHT, HTTOP, HTBOTTOM,
                 HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT}

    # --- fix argtypes on our private DLL instance ----------------------------
    _u32.GetWindowLongW.restype  = ctypes.c_long
    _u32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
    _u32.SetWindowLongW.restype  = ctypes.c_long
    _u32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_long]
    _u32.GetWindowLongPtrW.restype  = ctypes.c_ssize_t
    _u32.GetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int]
    _u32.SetWindowLongPtrW.restype  = ctypes.c_ssize_t
    _u32.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_ssize_t]
    _u32.CallWindowProcW.restype  = ctypes.c_ssize_t
    _u32.CallWindowProcW.argtypes = [ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    _u32.DefWindowProcW.restype  = ctypes.c_ssize_t
    _u32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    _u32.GetWindowRect.restype  = ctypes.c_bool
    _u32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
    _u32.SetWindowPos.restype  = ctypes.c_bool
    _u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, wt.UINT]

    # --- style: REMOVE WS_CAPTION, add WS_THICKFRAME -------------------------
    old_style = _u32.GetWindowLongW(hwnd, GWL_STYLE)
    new_style  = (old_style & ~WS_CAPTION) | WS_THICKFRAME | WS_SYSMENU | WS_MAXIMIZEBOX | WS_MINIMIZEBOX
    _u32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
    print(f"install_aero_and_resize: style {old_style:#010x} -> {new_style:#010x}")

    # --- Aero drop shadow + border via DWM -----------------------------------
    class MARGINS(ctypes.Structure):
        _fields_ = [
            ("cxLeftWidth",    ctypes.c_int),
            ("cxRightWidth",   ctypes.c_int),
            ("cyTopHeight",    ctypes.c_int),
            ("cyBottomHeight", ctypes.c_int),
        ]
    dwm.DwmExtendFrameIntoClientArea.argtypes = [wt.HWND, ctypes.POINTER(MARGINS)]
    dwm.DwmExtendFrameIntoClientArea.restype  = ctypes.c_long
    dwm.DwmSetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
    dwm.DwmSetWindowAttribute.restype = ctypes.c_long
    try:
        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(MARGINS(1, 1, 1, 1)))
    except Exception as exc:
        print(f"DwmExtendFrameIntoClientArea failed: {exc}")
    try:
        # DWMWA_BORDER_COLOR = 34. A visible border gives users an edge target
        # while keeping the frameless client-drawn titlebar.
        _border_color = ctypes.c_uint32(WINDOW_BORDER_COLOR)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(_border_color), ctypes.sizeof(_border_color))
    except Exception as exc:
        print(f"DwmSetWindowAttribute BORDER_COLOR failed: {exc}")

    # --- WndProc subclass (ctypes, explicit 64-bit argtypes) -----------------
    WndProcT = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
    WndEnumProcT = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    _u32.EnumChildWindows.restype = wt.BOOL
    _u32.EnumChildWindows.argtypes = [wt.HWND, WndEnumProcT, wt.LPARAM]
    old_proc: list[int] = [0]

    def _resize_hit_test(target_hwnd: int, x: int, y: int) -> int:
        rc = wt.RECT()
        if not _u32.GetWindowRect(target_hwnd, ctypes.byref(rc)):
            return HTCLIENT
        bw = RESIZE_HANDLE_W
        on_left   = x <  rc.left   + bw
        on_right  = x >= rc.right  - bw
        on_top    = y <  rc.top    + bw
        on_bottom = y >= rc.bottom - bw

        if on_top    and on_left:  return HTTOPLEFT
        if on_top    and on_right: return HTTOPRIGHT
        if on_bottom and on_left:  return HTBOTTOMLEFT
        if on_bottom and on_right: return HTBOTTOMRIGHT
        if on_left:                return HTLEFT
        if on_right:               return HTRIGHT
        if on_bottom:              return HTBOTTOM
        if on_top:                 return HTTOP
        return HTCLIENT

    def _install_child_edge_passthrough() -> None:
        # WebView child HWNDs cover the frameless client area. Returning
        # HTTRANSPARENT near the outer edge lets the top-level HWND receive the
        # hit test and enter the native resize loop.
        def _enum_child(child: int, _lp: int) -> bool:
            child_hwnd = int(child)
            if child_hwnd in _win_child_proc_installed:
                return True

            old_child_proc: list[int] = [0]

            def _child_proc(ch: int, msg: int, wp: int, lp: int) -> int:
                try:
                    if msg == WM_NCHITTEST:
                        x = ctypes.c_short(lp & 0xFFFF).value
                        y = ctypes.c_short((lp >> 16) & 0xFFFF).value
                        if _resize_hit_test(hwnd, x, y) in RESIZE_HT:
                            return HTTRANSPARENT
                except Exception as exc:
                    print(f"_child_proc error (msg={msg:#06x}): {exc}")
                return _u32.CallWindowProcW(old_child_proc[0], ch, msg, wp, lp)

            child_cb = WndProcT(_child_proc)
            child_cb_ptr = ctypes.cast(child_cb, ctypes.c_void_p).value or 0
            old_child_proc[0] = _u32.SetWindowLongPtrW(child, GWLP_WNDPROC, child_cb_ptr)
            if old_child_proc[0] == 0:
                err = ctypes.windll.kernel32.GetLastError()
                print(f"install_aero_and_resize: child WndProc failed for {child_hwnd:#010x}, GetLastError={err}")
                return True

            _win_child_proc_installed.add(child_hwnd)
            _win_hook_refs.extend([child_cb, old_child_proc])
            print(f"install_aero_and_resize: child WndProc installed on {child_hwnd:#010x}")
            return True

        enum_cb = WndEnumProcT(_enum_child)
        _u32.EnumChildWindows(hwnd, enum_cb, 0)
        _win_hook_refs.append(enum_cb)

    def _proc(h: int, msg: int, wp: int, lp: int) -> int:
        try:
            if msg == WM_NCCALCSIZE and wp:
                return 0

            if msg == WM_NCHITTEST:
                x = ctypes.c_short(lp & 0xFFFF).value
                y = ctypes.c_short((lp >> 16) & 0xFFFF).value
                rc = wt.RECT()
                _u32.GetWindowRect(h, ctypes.byref(rc))
                resize_hit = _resize_hit_test(h, x, y)
                if resize_hit in RESIZE_HT:
                    return resize_hit

                in_titlebar = y < rc.top + TITLE_BAR_H
                in_buttons  = x >= rc.right - BUTTON_W
                if in_titlebar and not in_buttons:
                    return HTCAPTION
                return HTCLIENT

            if msg == WM_NCACTIVATE:
                return _u32.DefWindowProcW(h, msg, wp, -1)

            # Forward resize clicks to DefWindowProc so Windows enters its
            # native size-move loop. WinForms swallows these NC mouse-down
            # events and never reaches DefWindowProc.
            if msg == WM_NCLBUTTONDOWN and wp in RESIZE_HT:
                return _u32.DefWindowProcW(h, msg, wp, lp)

            if msg == WM_NCLBUTTONDBLCLK and wp == HTCAPTION:
                threading.Thread(target=on_maximize, daemon=True).start()
                return 0

        except Exception as exc:
            print(f"_proc error (msg={msg:#06x}): {exc}")

        return _u32.CallWindowProcW(old_proc[0], h, msg, wp, lp)

    if not _win_proc_installed:
        cb = WndProcT(_proc)
        cb_ptr = ctypes.cast(cb, ctypes.c_void_p).value or 0
        old_proc[0] = _u32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, cb_ptr)
        if old_proc[0] == 0:
            err = ctypes.windll.kernel32.GetLastError()
            print(f"install_aero_and_resize: SetWindowLongPtrW failed, GetLastError={err}")
        else:
            _win_proc_installed = True
            print(f"install_aero_and_resize: WndProc installed, old={old_proc[0]:#018x}")
        _win_hook_refs.extend([cb, old_proc, _u32])
    else:
        print("install_aero_and_resize: WndProc already installed, refreshing frame only")
    _install_child_edge_passthrough()

    # Nudge the window by 1px then back so Windows fires WM_SIZE, which
    # activates the resize grip zones.  SetWindowPos with the same rect (even
    # with FRAMECHANGED) does not fire WM_SIZE and the grips stay dormant.
    # Two back-to-back calls happen before the compositor paints a new frame,
    # so the user never sees a flicker.
    rc = wt.RECT()
    _u32.GetWindowRect(hwnd, ctypes.byref(rc))
    x = int(rc.left)
    y = int(rc.top)
    w = int(rc.right  - rc.left)
    h = int(rc.bottom - rc.top)
    _u32.SetWindowPos(hwnd, 0, x, y, w + 1, h, SWP_NOZORDER | SWP_NOACTIVATE)
    _u32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER | SWP_FRAMECHANGED | SWP_NOACTIVATE)
    print("install_aero_and_resize: done")
