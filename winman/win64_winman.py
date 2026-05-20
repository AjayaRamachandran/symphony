# winman/win64_winman.py
# Windows ctypes, WndProc, and Aero handlers for the frameless Symphony window.

from __future__ import annotations
import sys

TITLE_BAR_H = 30   # must match title-bar.css: .titlebar { height: 30px }
BUTTON_W    = 108  # 3 × 36 px window-controls buttons
RESIZE_HANDLE_W = 6   # invisible resize handle width in screen pixels
WINDOW_BORDER_COLOR = 0x00404040  # COLORREF for a neutral gray DWM border

_win_hook_refs: list = []       # prevent GC of ctypes WndProc callbacks
_win_proc_installed: bool = False
_manual_resize_start: dict | None = None
_drag_refs: list = []           # keep COM drag-source callbacks alive
_drop_target_refs: list = []    # keep COM drop-target callbacks alive
_drop_target_installed: bool = False
_pending_drag_paths: list[str] = []  # paths waiting to be picked up on the UI thread

# Custom window message asking the WebView's UI thread to enter DoDragDrop.
# Tauri uses the same trick (run_on_main_thread + DoDragDrop). Running the
# modal drag from a worker thread races SetCapture against Chromium and kills
# the in-progress HTML5 drag, so we hop to the UI thread via the existing
# WndProc subclass instead.
WM_APP_DRAG = 0x8001  # WM_APP + 1


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
                # NOTE: we intentionally leave AllowExternalDrop at its
                # default True so the WebView's HTML5 drop handlers
                # (Files.jsx, Directory.jsx) keep receiving external file
                # drops via dataTransfer.files. The IDropTarget registered
                # on the host HWND is therefore a "shadow" that mostly does
                # not fire, which is fine until we have a separate plan for
                # path-based drop-in that does not break the existing base64
                # fallback.

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


def _get_hwnd(main_window) -> int:
    """Return the pywebview top-level HWND, or 0 if it cannot be resolved."""
    import ctypes

    hwnd: int = 0
    native = getattr(main_window, "native", None)
    if native is not None:
        try:
            handle = native.Handle
            hwnd = handle.ToInt64() if hasattr(handle, "ToInt64") else handle.ToInt32()
        except Exception as exc:
            print(f"win_c: Handle conversion failed: {exc}")
    if not hwnd:
        hwnd = ctypes.windll.user32.FindWindowW(None, getattr(main_window, "title", "Symphony"))
    return int(hwnd or 0)


def post_native_drag(main_window, file_paths) -> bool:
    """Schedule a native shell drag on the WebView's UI thread.

    Stashes ``file_paths`` and PostMessageW's ``WM_APP_DRAG`` to the host
    HWND. The WndProc subclass installed by ``install_aero_and_resize`` picks
    it up on the next message pump and calls ``DoDragDrop`` synchronously on
    that thread.

    Why bother: ``DoDragDrop`` is modal and grabs mouse capture for the
    calling thread. Running it from a worker thread races SetCapture against
    Chromium's HTML5 drag and silently kills the in-app drag, which is the
    bug we hit on the first pass. Tauri's ``tauri-plugin-drag`` solves the
    same problem the same way (run_on_main_thread + DoDragDrop)."""
    if sys.platform != "win32" or not main_window or not file_paths:
        return False

    import ctypes
    import ctypes.wintypes as wt
    import os

    if isinstance(file_paths, (str, bytes, os.PathLike)):
        paths = [str(file_paths)]
    else:
        paths = [str(p) for p in file_paths if p]
    if not paths:
        return False

    hwnd = _get_hwnd(main_window)
    if not hwnd:
        print("[symphony-drag] post_native_drag: could not obtain HWND")
        return False

    global _pending_drag_paths
    _pending_drag_paths = paths

    user32 = ctypes.WinDLL("user32")
    user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    user32.PostMessageW.restype = wt.BOOL

    ok = bool(user32.PostMessageW(hwnd, WM_APP_DRAG, 0, 0))
    print(f"[symphony-drag] post_native_drag PostMessage ok={ok} paths={paths}")
    return ok


def start_file_drag(file_paths) -> bool:
    """Start a native Windows shell file drag for the given path(s).

    MUST be invoked on the WebView's UI thread; see ``post_native_drag``.

    Accepts either a single path string or a list of paths so callers can drag
    multiple files at once. Missing files are filtered out; if nothing remains,
    the call is a no-op."""
    if sys.platform != "win32" or not file_paths:
        return False

    import ctypes
    import ctypes.wintypes as wt
    import os

    if isinstance(file_paths, (str, bytes, os.PathLike)):
        raw_paths = [file_paths]
    else:
        raw_paths = list(file_paths)

    resolved: list[str] = []
    for entry in raw_paths:
        if not entry:
            continue
        absolute = os.path.abspath(str(entry))
        if not os.path.isfile(absolute):
            print(f"start_file_drag: file does not exist: {absolute}")
            continue
        resolved.append(absolute)
    if not resolved:
        print("[symphony-drag] start_file_drag: no resolvable paths")
        return False
    print(f"[symphony-drag] start_file_drag resolved={resolved}")

    HRESULT = ctypes.c_long
    ULONG = wt.DWORD
    DWORD = wt.DWORD
    LONG = ctypes.c_long
    CLIPFORMAT = wt.WORD
    LPVOID = wt.LPVOID

    S_OK = 0
    E_NOTIMPL = ctypes.c_long(0x80004001).value
    E_NOINTERFACE = ctypes.c_long(0x80004002).value
    DV_E_FORMATETC = ctypes.c_long(0x80040064).value
    DRAGDROP_S_DROP = 0x00040100
    DRAGDROP_S_CANCEL = 0x00040101
    DRAGDROP_S_USEDEFAULTCURSORS = 0x00040102

    CF_HDROP = 15
    DVASPECT_CONTENT = 1
    TYMED_HGLOBAL = 1
    GMEM_MOVEABLE = 0x0002
    GMEM_ZEROINIT = 0x0040
    MK_LBUTTON = 0x0001
    DROPEFFECT_COPY = 1

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", DWORD),
            ("Data2", wt.WORD),
            ("Data3", wt.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    def guid(data1: int, data2: int, data3: int, data4: tuple[int, ...]) -> GUID:
        return GUID(data1, data2, data3, (ctypes.c_ubyte * 8)(*data4))

    IID_IUNKNOWN = guid(0x00000000, 0x0000, 0x0000, (0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46))
    IID_IDATAOBJECT = guid(0x0000010E, 0x0000, 0x0000, (0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46))
    IID_IDROPSOURCE = guid(0x00000121, 0x0000, 0x0000, (0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46))

    def same_guid(a, b: GUID) -> bool:
        return bool(ctypes.string_at(a, ctypes.sizeof(GUID)) == ctypes.string_at(ctypes.byref(b), ctypes.sizeof(GUID)))

    class FORMATETC(ctypes.Structure):
        _fields_ = [
            ("cfFormat", CLIPFORMAT),
            ("ptd", LPVOID),
            ("dwAspect", DWORD),
            ("lindex", LONG),
            ("tymed", DWORD),
        ]

    class STGMEDIUM(ctypes.Structure):
        _fields_ = [
            ("tymed", DWORD),
            ("hGlobal", wt.HGLOBAL),
            ("pUnkForRelease", LPVOID),
        ]

    class DROPFILES(ctypes.Structure):
        _fields_ = [
            ("pFiles", DWORD),
            ("pt", wt.POINT),
            ("fNC", wt.BOOL),
            ("fWide", wt.BOOL),
        ]

    def make_hdrop(path_values) -> int:
        if isinstance(path_values, str):
            joined = path_values + "\0\0"
        else:
            joined = "\0".join(path_values) + "\0\0"
        encoded = joined.encode("utf-16le")
        header_size = ctypes.sizeof(DROPFILES)
        total_size = header_size + len(encoded)
        kernel32 = ctypes.windll.kernel32
        kernel32.GlobalAlloc.restype = wt.HGLOBAL
        kernel32.GlobalAlloc.argtypes = [wt.UINT, ctypes.c_size_t]
        kernel32.GlobalLock.restype = LPVOID
        kernel32.GlobalLock.argtypes = [wt.HGLOBAL]
        kernel32.GlobalUnlock.restype = wt.BOOL
        kernel32.GlobalUnlock.argtypes = [wt.HGLOBAL]

        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, total_size)
        if not handle:
            raise OSError("GlobalAlloc failed")

        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            raise OSError("GlobalLock failed")

        drop = DROPFILES()
        drop.pFiles = header_size
        drop.fWide = True
        ctypes.memmove(ptr, ctypes.byref(drop), header_size)
        ctypes.memmove(ptr + header_size, encoded, len(encoded))
        kernel32.GlobalUnlock(handle)
        return int(handle)

    class DataObject(ctypes.Structure):
        pass

    class DropSource(ctypes.Structure):
        pass

    DataObjectPtr = ctypes.POINTER(DataObject)
    DropSourcePtr = ctypes.POINTER(DropSource)

    DataQueryInterface = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr, ctypes.POINTER(GUID), ctypes.POINTER(LPVOID))
    DataAddRef = ctypes.WINFUNCTYPE(ULONG, DataObjectPtr)
    DataRelease = ctypes.WINFUNCTYPE(ULONG, DataObjectPtr)
    GetData = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr, ctypes.POINTER(FORMATETC), ctypes.POINTER(STGMEDIUM))
    QueryGetData = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr, ctypes.POINTER(FORMATETC))
    DataSimple = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr)
    DataFormatSimple = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr, ctypes.POINTER(FORMATETC), ctypes.POINTER(FORMATETC))
    DataSetData = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr, ctypes.POINTER(FORMATETC), ctypes.POINTER(STGMEDIUM), wt.BOOL)
    DataDAdvise = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr, ctypes.POINTER(FORMATETC), DWORD, LPVOID, ctypes.POINTER(DWORD))
    DataDUnadvise = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr, DWORD)
    DataEnum = ctypes.WINFUNCTYPE(HRESULT, DataObjectPtr, ctypes.POINTER(LPVOID))

    SourceQueryInterface = ctypes.WINFUNCTYPE(HRESULT, DropSourcePtr, ctypes.POINTER(GUID), ctypes.POINTER(LPVOID))
    SourceAddRef = ctypes.WINFUNCTYPE(ULONG, DropSourcePtr)
    SourceRelease = ctypes.WINFUNCTYPE(ULONG, DropSourcePtr)
    QueryContinueDrag = ctypes.WINFUNCTYPE(HRESULT, DropSourcePtr, wt.BOOL, DWORD)
    GiveFeedback = ctypes.WINFUNCTYPE(HRESULT, DropSourcePtr, DWORD)

    class DataObjectVtbl(ctypes.Structure):
        _fields_ = [
            ("QueryInterface", DataQueryInterface),
            ("AddRef", DataAddRef),
            ("Release", DataRelease),
            ("GetData", GetData),
            ("GetDataHere", GetData),
            ("QueryGetData", QueryGetData),
            ("GetCanonicalFormatEtc", DataFormatSimple),
            ("SetData", DataSetData),
            ("EnumFormatEtc", DataEnum),
            ("DAdvise", DataDAdvise),
            ("DUnadvise", DataDUnadvise),
            ("EnumDAdvise", DataEnum),
        ]

    class DropSourceVtbl(ctypes.Structure):
        _fields_ = [
            ("QueryInterface", SourceQueryInterface),
            ("AddRef", SourceAddRef),
            ("Release", SourceRelease),
            ("QueryContinueDrag", QueryContinueDrag),
            ("GiveFeedback", GiveFeedback),
        ]

    DataObject._fields_ = [
        ("lpVtbl", ctypes.POINTER(DataObjectVtbl)),
        ("refCount", ULONG),
        ("filePaths", ctypes.py_object),
    ]
    DropSource._fields_ = [
        ("lpVtbl", ctypes.POINTER(DropSourceVtbl)),
        ("refCount", ULONG),
    ]

    def accepts_hdrop(fmt: FORMATETC) -> bool:
        return bool(
            fmt.cfFormat == CF_HDROP
            and fmt.dwAspect == DVASPECT_CONTENT
            and (fmt.tymed & TYMED_HGLOBAL)
        )

    @DataQueryInterface
    def data_query_interface(this, riid, ppv):
        if same_guid(riid, IID_IUNKNOWN) or same_guid(riid, IID_IDATAOBJECT):
            ppv[0] = ctypes.cast(this, LPVOID)
            data_add_ref(this)
            return S_OK
        ppv[0] = None
        return E_NOINTERFACE

    @DataAddRef
    def data_add_ref(this):
        this.contents.refCount += 1
        return this.contents.refCount

    @DataRelease
    def data_release(this):
        if this.contents.refCount:
            this.contents.refCount -= 1
        return this.contents.refCount

    @GetData
    def data_get_data(this, pformatetc, pmedium):
        if not pformatetc or not pmedium or not accepts_hdrop(pformatetc.contents):
            return DV_E_FORMATETC
        try:
            pmedium.contents.tymed = TYMED_HGLOBAL
            pmedium.contents.hGlobal = make_hdrop(list(this.contents.filePaths))
            pmedium.contents.pUnkForRelease = None
            return S_OK
        except Exception as exc:
            print(f"start_file_drag GetData failed: {exc}")
            return DV_E_FORMATETC

    @GetData
    def data_get_data_here(_this, _pformatetc, _pmedium):
        return E_NOTIMPL

    @QueryGetData
    def data_query_get_data(_this, pformatetc):
        if pformatetc and accepts_hdrop(pformatetc.contents):
            return S_OK
        return DV_E_FORMATETC

    @DataFormatSimple
    def data_format_simple(_this, _pformatetc_in, _pformatetc_out):
        return E_NOTIMPL

    @DataSetData
    def data_set_data(_this, _pformatetc, _pmedium, _release):
        return E_NOTIMPL

    @DataEnum
    def data_enum(_this, _ppenum):
        return E_NOTIMPL

    @DataDAdvise
    def data_dadvise(_this, _pformatetc, _advf, _sink, _connection):
        return E_NOTIMPL

    @DataDUnadvise
    def data_dunadvise(_this, _connection):
        return E_NOTIMPL

    @SourceQueryInterface
    def source_query_interface(this, riid, ppv):
        if same_guid(riid, IID_IUNKNOWN) or same_guid(riid, IID_IDROPSOURCE):
            ppv[0] = ctypes.cast(this, LPVOID)
            source_add_ref(this)
            return S_OK
        ppv[0] = None
        return E_NOINTERFACE

    @SourceAddRef
    def source_add_ref(this):
        this.contents.refCount += 1
        return this.contents.refCount

    @SourceRelease
    def source_release(this):
        if this.contents.refCount:
            this.contents.refCount -= 1
        return this.contents.refCount

    @QueryContinueDrag
    def source_query_continue_drag(_this, escape_pressed, key_state):
        if escape_pressed:
            return DRAGDROP_S_CANCEL
        if not (key_state & MK_LBUTTON):
            return DRAGDROP_S_DROP
        return S_OK

    @GiveFeedback
    def source_give_feedback(_this, _effect):
        return DRAGDROP_S_USEDEFAULTCURSORS

    data_vtbl = DataObjectVtbl(
        data_query_interface,
        data_add_ref,
        data_release,
        data_get_data,
        data_get_data_here,
        data_query_get_data,
        data_format_simple,
        data_set_data,
        data_enum,
        data_dadvise,
        data_dunadvise,
        data_enum,
    )
    source_vtbl = DropSourceVtbl(
        source_query_interface,
        source_add_ref,
        source_release,
        source_query_continue_drag,
        source_give_feedback,
    )
    data_object = DataObject(ctypes.pointer(data_vtbl), 1, resolved)
    drop_source = DropSource(ctypes.pointer(source_vtbl), 1)

    ole32 = ctypes.OleDLL("ole32")
    ole32.OleInitialize.argtypes = [LPVOID]
    ole32.OleInitialize.restype = HRESULT
    ole32.DoDragDrop.argtypes = [LPVOID, LPVOID, DWORD, ctypes.POINTER(DWORD)]
    ole32.DoDragDrop.restype = HRESULT

    effect = DWORD(0)
    refs = [
        data_vtbl,
        source_vtbl,
        data_object,
        drop_source,
        data_query_interface,
        data_add_ref,
        data_release,
        data_get_data,
        data_get_data_here,
        data_query_get_data,
        data_format_simple,
        data_set_data,
        data_enum,
        data_dadvise,
        data_dunadvise,
        source_query_interface,
        source_add_ref,
        source_release,
        source_query_continue_drag,
        source_give_feedback,
    ]
    _drag_refs.append(refs)
    ole_initialized = False
    try:
        init_result = ole32.OleInitialize(None)
        ole_initialized = init_result >= 0
        result = ole32.DoDragDrop(
            ctypes.cast(ctypes.byref(data_object), LPVOID),
            ctypes.cast(ctypes.byref(drop_source), LPVOID),
            DROPEFFECT_COPY,
            ctypes.byref(effect),
        )
        if result not in (S_OK, DRAGDROP_S_DROP, DRAGDROP_S_CANCEL):
            print(f"start_file_drag: DoDragDrop returned {result:#010x}")
            return False
        return True
    except Exception as exc:
        print(f"start_file_drag failed: {exc}")
        return False
    finally:
        try:
            _drag_refs.remove(refs)
        except ValueError:
            pass
        if ole_initialized:
            try:
                ole32.OleUninitialize()
            except Exception:
                pass


def register_drop_target(main_window, on_paths) -> bool:
    """Register a Win32 IDropTarget on the host HWND so OS drops surface as
    real filesystem paths instead of base64 byte streams.

    ``on_paths`` is invoked with ``(paths: list[str], screen_x: int,
    screen_y: int)`` whenever the user releases a shell drag over the window.
    Pairs with ``patch_webview_nonclient`` setting ``AllowExternalDrop=False``
    so WebView2 stops swallowing external drops; HTML5 drag-and-drop within
    the WebView (in-app file moves) is unaffected."""
    global _drop_target_installed
    if sys.platform != "win32" or not main_window or _drop_target_installed:
        return _drop_target_installed

    import ctypes
    import ctypes.wintypes as wt

    hwnd = _get_hwnd(main_window)
    if not hwnd:
        print("register_drop_target: could not obtain HWND")
        return False

    HRESULT = ctypes.c_long
    ULONG = wt.DWORD
    DWORD = wt.DWORD
    LONG = ctypes.c_long
    CLIPFORMAT = wt.WORD
    LPVOID = wt.LPVOID

    S_OK = 0
    E_NOINTERFACE = ctypes.c_long(0x80004002).value

    CF_HDROP = 15
    DVASPECT_CONTENT = 1
    TYMED_HGLOBAL = 1
    DROPEFFECT_NONE = 0
    DROPEFFECT_COPY = 1

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", DWORD),
            ("Data2", wt.WORD),
            ("Data3", wt.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    def guid(d1: int, d2: int, d3: int, d4: tuple[int, ...]) -> GUID:
        return GUID(d1, d2, d3, (ctypes.c_ubyte * 8)(*d4))

    IID_IUNKNOWN = guid(0x00000000, 0x0000, 0x0000, (0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46))
    IID_IDROPTARGET = guid(0x00000122, 0x0000, 0x0000, (0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46))

    def same_guid(a, b: GUID) -> bool:
        return bool(
            ctypes.string_at(a, ctypes.sizeof(GUID))
            == ctypes.string_at(ctypes.byref(b), ctypes.sizeof(GUID))
        )

    class FORMATETC(ctypes.Structure):
        _fields_ = [
            ("cfFormat", CLIPFORMAT),
            ("ptd", LPVOID),
            ("dwAspect", DWORD),
            ("lindex", LONG),
            ("tymed", DWORD),
        ]

    class STGMEDIUM(ctypes.Structure):
        _fields_ = [
            ("tymed", DWORD),
            ("hGlobal", wt.HGLOBAL),
            ("pUnkForRelease", LPVOID),
        ]

    class POINTL(ctypes.Structure):
        _fields_ = [("x", LONG), ("y", LONG)]

    # IDataObject vtable layout (we only call GetData/QueryGetData so we just
    # need pointers at the right offsets through generic vtable access).
    LPUNKNOWN = LPVOID

    class DropTarget(ctypes.Structure):
        pass

    DropTargetPtr = ctypes.POINTER(DropTarget)

    QueryInterfaceFn = ctypes.WINFUNCTYPE(HRESULT, DropTargetPtr, ctypes.POINTER(GUID), ctypes.POINTER(LPVOID))
    AddRefFn = ctypes.WINFUNCTYPE(ULONG, DropTargetPtr)
    ReleaseFn = ctypes.WINFUNCTYPE(ULONG, DropTargetPtr)
    DragEnterFn = ctypes.WINFUNCTYPE(HRESULT, DropTargetPtr, LPVOID, DWORD, POINTL, ctypes.POINTER(DWORD))
    DragOverFn = ctypes.WINFUNCTYPE(HRESULT, DropTargetPtr, DWORD, POINTL, ctypes.POINTER(DWORD))
    DragLeaveFn = ctypes.WINFUNCTYPE(HRESULT, DropTargetPtr)
    DropFn = ctypes.WINFUNCTYPE(HRESULT, DropTargetPtr, LPVOID, DWORD, POINTL, ctypes.POINTER(DWORD))

    class DropTargetVtbl(ctypes.Structure):
        _fields_ = [
            ("QueryInterface", QueryInterfaceFn),
            ("AddRef", AddRefFn),
            ("Release", ReleaseFn),
            ("DragEnter", DragEnterFn),
            ("DragOver", DragOverFn),
            ("DragLeave", DragLeaveFn),
            ("Drop", DropFn),
        ]

    DropTarget._fields_ = [
        ("lpVtbl", ctypes.POINTER(DropTargetVtbl)),
        ("refCount", ULONG),
    ]

    ole32 = ctypes.OleDLL("ole32")
    ole32.OleInitialize.argtypes = [LPVOID]
    ole32.OleInitialize.restype = HRESULT
    ole32.RegisterDragDrop.argtypes = [wt.HWND, LPVOID]
    ole32.RegisterDragDrop.restype = HRESULT
    ole32.ReleaseStgMedium.argtypes = [ctypes.POINTER(STGMEDIUM)]
    ole32.ReleaseStgMedium.restype = None

    shell32 = ctypes.windll.shell32
    shell32.DragQueryFileW.argtypes = [wt.HGLOBAL, wt.UINT, wt.LPWSTR, wt.UINT]
    shell32.DragQueryFileW.restype = wt.UINT

    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalLock.restype = LPVOID
    kernel32.GlobalLock.argtypes = [wt.HGLOBAL]
    kernel32.GlobalUnlock.restype = wt.BOOL
    kernel32.GlobalUnlock.argtypes = [wt.HGLOBAL]

    @QueryInterfaceFn
    def query_interface(this, riid, ppv):
        if same_guid(riid, IID_IUNKNOWN) or same_guid(riid, IID_IDROPTARGET):
            ppv[0] = ctypes.cast(this, LPVOID)
            add_ref(this)
            return S_OK
        ppv[0] = None
        return E_NOINTERFACE

    @AddRefFn
    def add_ref(this):
        this.contents.refCount += 1
        return this.contents.refCount

    @ReleaseFn
    def release(this):
        if this.contents.refCount:
            this.contents.refCount -= 1
        return this.contents.refCount

    def _has_hdrop(data_object_ptr) -> bool:
        # Build a FORMATETC for CF_HDROP and call IDataObject::QueryGetData
        # via vtable index 3 (IUnknown has 3 entries; QueryGetData is the 4th
        # method on IDataObject).
        fmt = FORMATETC(CF_HDROP, None, DVASPECT_CONTENT, -1, TYMED_HGLOBAL)
        try:
            vtbl_ptr = ctypes.cast(
                data_object_ptr, ctypes.POINTER(ctypes.POINTER(LPVOID))
            )
            vtbl = vtbl_ptr.contents
            fn_ptr = vtbl[4]  # QueryGetData
            QueryGetDataT = ctypes.WINFUNCTYPE(HRESULT, LPVOID, ctypes.POINTER(FORMATETC))
            fn = ctypes.cast(fn_ptr, QueryGetDataT)
            return fn(data_object_ptr, ctypes.byref(fmt)) == S_OK
        except Exception as exc:  # noqa: BLE001
            print(f"register_drop_target QueryGetData failed: {exc}")
            return False

    def _read_paths(data_object_ptr) -> list[str]:
        fmt = FORMATETC(CF_HDROP, None, DVASPECT_CONTENT, -1, TYMED_HGLOBAL)
        medium = STGMEDIUM()
        try:
            vtbl_ptr = ctypes.cast(
                data_object_ptr, ctypes.POINTER(ctypes.POINTER(LPVOID))
            )
            vtbl = vtbl_ptr.contents
            fn_ptr = vtbl[3]  # GetData
            GetDataT = ctypes.WINFUNCTYPE(
                HRESULT, LPVOID, ctypes.POINTER(FORMATETC), ctypes.POINTER(STGMEDIUM)
            )
            fn = ctypes.cast(fn_ptr, GetDataT)
            hr = fn(data_object_ptr, ctypes.byref(fmt), ctypes.byref(medium))
            if hr != S_OK or not medium.hGlobal:
                return []
            ptr = kernel32.GlobalLock(medium.hGlobal)
            if not ptr:
                return []
            try:
                count = shell32.DragQueryFileW(medium.hGlobal, 0xFFFFFFFF, None, 0)
                paths: list[str] = []
                for i in range(count):
                    needed = shell32.DragQueryFileW(medium.hGlobal, i, None, 0)
                    if needed <= 0:
                        continue
                    buf = ctypes.create_unicode_buffer(needed + 1)
                    shell32.DragQueryFileW(medium.hGlobal, i, buf, needed + 1)
                    if buf.value:
                        paths.append(buf.value)
                return paths
            finally:
                kernel32.GlobalUnlock(medium.hGlobal)
                ole32.ReleaseStgMedium(ctypes.byref(medium))
        except Exception as exc:  # noqa: BLE001
            print(f"register_drop_target GetData failed: {exc}")
            return []

    state = {"accept": False}

    @DragEnterFn
    def drag_enter(this, p_data_object, _key_state, _pt, p_effect):
        accept = _has_hdrop(p_data_object)
        state["accept"] = accept
        print(f"[symphony-drag] IDropTarget.DragEnter accept={accept}")
        if p_effect:
            p_effect[0] = DROPEFFECT_COPY if accept else DROPEFFECT_NONE
        return S_OK

    @DragOverFn
    def drag_over(_this, _key_state, _pt, p_effect):
        if p_effect:
            p_effect[0] = DROPEFFECT_COPY if state["accept"] else DROPEFFECT_NONE
        return S_OK

    @DragLeaveFn
    def drag_leave(_this):
        print("[symphony-drag] IDropTarget.DragLeave")
        state["accept"] = False
        return S_OK

    @DropFn
    def drop(_this, p_data_object, _key_state, pt, p_effect):
        print(f"[symphony-drag] IDropTarget.Drop at ({int(pt.x)},{int(pt.y)})")
        try:
            paths = _read_paths(p_data_object)
            print(f"[symphony-drag] IDropTarget paths={paths}")
            if paths:
                try:
                    on_paths(paths, int(pt.x), int(pt.y))
                except Exception as exc:  # noqa: BLE001
                    print(f"[symphony-drag] on_paths failed: {exc}")
        finally:
            state["accept"] = False
            if p_effect:
                p_effect[0] = DROPEFFECT_COPY
        return S_OK

    vtbl = DropTargetVtbl(
        query_interface, add_ref, release,
        drag_enter, drag_over, drag_leave, drop,
    )
    target = DropTarget(ctypes.pointer(vtbl), 1)

    try:
        ole32.OleInitialize(None)
    except Exception as exc:  # noqa: BLE001
        print(f"register_drop_target OleInitialize failed: {exc}")

    hr = ole32.RegisterDragDrop(hwnd, ctypes.cast(ctypes.byref(target), LPVOID))
    if hr != S_OK:
        print(f"register_drop_target: RegisterDragDrop returned {hr:#010x}")
        return False

    _drop_target_refs.extend([
        vtbl, target,
        query_interface, add_ref, release,
        drag_enter, drag_over, drag_leave, drop,
        state, on_paths,
    ])
    _drop_target_installed = True
    print(f"register_drop_target: installed on HWND {hwnd:#010x}")
    return True


def start_resize(main_window, edge: str) -> bool:
    """Start the native Windows resize loop for a frameless pywebview window."""
    if sys.platform != "win32" or not main_window:
        return False

    import ctypes
    import ctypes.wintypes as wt

    wmsz_by_edge = {
        "left": 1,
        "right": 2,
        "top": 3,
        "top-left": 4,
        "top-right": 5,
        "bottom": 6,
        "bottom-left": 7,
        "bottom-right": 8,
    }
    wmsz = wmsz_by_edge.get(edge)
    if wmsz is None:
        return False

    hwnd = _get_hwnd(main_window)
    if not hwnd:
        print("start_resize: could not obtain HWND")
        return False

    user32 = ctypes.WinDLL("user32")
    user32.ReleaseCapture.restype = ctypes.c_bool
    user32.SetForegroundWindow.restype = ctypes.c_bool
    user32.SetForegroundWindow.argtypes = [wt.HWND]
    user32.GetCursorPos.restype = ctypes.c_bool
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]

    WM_SYSCOMMAND = 0x0112
    SC_SIZE = 0xF000
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    lparam = (int(pt.y) << 16) | (int(pt.x) & 0xFFFF)

    user32.SetForegroundWindow(hwnd)
    user32.ReleaseCapture()
    user32.SendMessageW(hwnd, WM_SYSCOMMAND, SC_SIZE | wmsz, lparam)
    return True


def begin_manual_resize(main_window, edge: str, screen_x: int, screen_y: int) -> bool:
    """Capture initial geometry for JS-driven resizing of WebView-covered edges."""
    global _manual_resize_start
    if sys.platform != "win32" or not main_window:
        return False
    if edge not in {
        "left", "right", "top", "bottom",
        "top-left", "top-right", "bottom-left", "bottom-right",
    }:
        return False
    try:
        import ctypes
        import ctypes.wintypes as wt

        hwnd = _get_hwnd(main_window)
        if not hwnd:
            print("begin_manual_resize: could not obtain HWND")
            return False

        user32 = ctypes.WinDLL("user32")
        user32.GetCursorPos.restype = ctypes.c_bool
        user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
        user32.GetWindowRect.restype = ctypes.c_bool
        user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
        user32.GetDpiForWindow.restype = wt.UINT
        user32.GetDpiForWindow.argtypes = [wt.HWND]

        pt = wt.POINT()
        rc = wt.RECT()
        if not user32.GetCursorPos(ctypes.byref(pt)):
            pt.x = int(screen_x)
            pt.y = int(screen_y)
        if not user32.GetWindowRect(hwnd, ctypes.byref(rc)):
            return False

        try:
            dpi_scale = max(float(user32.GetDpiForWindow(hwnd)) / 96.0, 1.0)
        except Exception:
            dpi_scale = 1.0
        min_w, min_h = getattr(main_window, "min_size", (800, 800)) or (800, 800)

        _manual_resize_start = {
            "edge": edge,
            "hwnd": hwnd,
            "screen_x": int(pt.x),
            "screen_y": int(pt.y),
            "x": int(rc.left),
            "y": int(rc.top),
            "width": int(rc.right - rc.left),
            "height": int(rc.bottom - rc.top),
            "min_width": int(int(min_w) * dpi_scale),
            "min_height": int(int(min_h) * dpi_scale),
        }
        return True
    except Exception as exc:
        print(f"begin_manual_resize failed: {exc}")
        _manual_resize_start = None
        return False


def update_manual_resize(main_window, screen_x: int, screen_y: int) -> bool:
    """Apply JS-driven resize updates while dragging a custom edge handle."""
    if sys.platform != "win32" or not main_window or not _manual_resize_start:
        return False

    try:
        import ctypes
        import ctypes.wintypes as wt

        start = _manual_resize_start
        edge = str(start["edge"])
        hwnd = int(start["hwnd"])
        min_w = int(start["min_width"])
        min_h = int(start["min_height"])
        start_x = int(start["x"])
        start_y = int(start["y"])
        start_w = int(start["width"])
        start_h = int(start["height"])

        user32 = ctypes.WinDLL("user32")
        user32.GetCursorPos.restype = ctypes.c_bool
        user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
        user32.SetWindowPos.restype = ctypes.c_bool
        user32.SetWindowPos.argtypes = [
            wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wt.UINT,
        ]

        pt = wt.POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            cur_x = int(pt.x)
            cur_y = int(pt.y)
        else:
            cur_x = int(screen_x)
            cur_y = int(screen_y)
        dx = cur_x - int(start["screen_x"])
        dy = cur_y - int(start["screen_y"])

        new_x = start_x
        new_y = start_y
        new_w = start_w
        new_h = start_h

        if "left" in edge:
            dx = min(dx, start_w - min_w)
            new_x = start_x + dx
            new_w = start_w - dx
        elif "right" in edge:
            new_w = max(min_w, start_w + dx)

        if "top" in edge:
            dy = min(dy, start_h - min_h)
            new_y = start_y + dy
            new_h = start_h - dy
        elif "bottom" in edge:
            new_h = max(min_h, start_h + dy)

        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        return bool(user32.SetWindowPos(
            hwnd,
            0,
            int(new_x),
            int(new_y),
            int(new_w),
            int(new_h),
            SWP_NOZORDER | SWP_NOACTIVATE,
        ))
    except Exception as exc:
        print(f"update_manual_resize failed: {exc}")
        return False


def end_manual_resize() -> None:
    """Clear JS-driven resize state."""
    global _manual_resize_start
    _manual_resize_start = None


def toggle_native_maximize(main_window) -> bool | None:
    """Toggle native maximize/restore through the native system command path."""
    if sys.platform != "win32" or not main_window:
        return None

    import ctypes
    import ctypes.wintypes as wt

    hwnd = _get_hwnd(main_window)
    if not hwnd:
        print("toggle_native_maximize: could not obtain HWND")
        return None

    user32 = ctypes.WinDLL("user32")
    user32.IsZoomed.restype = ctypes.c_bool
    user32.IsZoomed.argtypes = [wt.HWND]
    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]

    WM_SYSCOMMAND = 0x0112
    SC_RESTORE = 0xF120
    SC_MAXIMIZE = 0xF030
    is_zoomed = bool(user32.IsZoomed(hwnd))
    user32.SendMessageW(hwnd, WM_SYSCOMMAND, SC_RESTORE if is_zoomed else SC_MAXIMIZE, 0)
    return not is_zoomed


def install_aero_and_resize(main_window, on_maximize) -> None:
    """Enable native resize borders, Aero drop shadow, and Aero Snap.

    Design:
      Style        WS_CAPTION + WS_THICKFRAME so DWM sees a normal overlapped
                   window while WM_NCCALCSIZE hides the native chrome.
      WM_NCCALCSIZE → 0   Collapses visible NC area; WS_THICKFRAME still
                          provides invisible resize grips at window edges.
      WM_NCHITTEST        Returns HTCAPTION for the title-bar drag strip so
                          the OS owns native drag and Aero Snap.  The button
                          zone (right BUTTON_W px) returns HTCLIENT so
                          WebView2 delivers those clicks to React normally.
                          Window edges return the appropriate resize codes.
      WM_NCACTIVATE       Forwarded with lParam=-1 to suppress NC repaint flash.
      WM_NCLBUTTONDBLCLK  Forwarded to DefWindowProc so Windows owns the native
                          maximize transition.
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
    hwnd = _get_hwnd(main_window)
    if not hwnd:
        print("install_aero_and_resize: could not obtain HWND — aborting")
        return

    print(f"install_aero_and_resize: HWND={hwnd:#010x}")

    # --- Win32 constants -----------------------------------------------------
    GWL_STYLE      = -16
    GWLP_WNDPROC   = -4
    WS_THICKFRAME  = 0x00040000
    WS_CAPTION     = 0x00C00000
    WS_SYSMENU     = 0x00080000
    WS_MAXIMIZEBOX = 0x00010000
    WS_MINIMIZEBOX = 0x00020000
    SWP_FRAMECHANGED = 0x0020
    SWP_NOACTIVATE   = 0x0010
    SWP_NOZORDER     = 0x0004
    SWP_NOSIZE       = 0x0001
    SWP_NOMOVE       = 0x0002

    WM_NCCALCSIZE      = 0x0083
    WM_GETMINMAXINFO   = 0x0024
    WM_NCHITTEST       = 0x0084
    WM_NCACTIVATE      = 0x0086
    WM_NCLBUTTONDOWN   = 0x00A1
    WM_NCLBUTTONDBLCLK = 0x00A3
    MONITOR_DEFAULTTONEAREST = 0x00000002

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
    RESIZE_HT = {HTLEFT, HTRIGHT, HTTOP, HTBOTTOM,
                 HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT}

    # --- fix argtypes on our private DLL instance ----------------------------
    _u32.GetWindowLongW.restype  = ctypes.c_long
    _u32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
    _u32.SetWindowLongW.restype  = ctypes.c_long
    _u32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_long]
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
    _u32.MonitorFromWindow.restype = wt.HANDLE
    _u32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
    _u32.GetMonitorInfoW.restype = ctypes.c_bool
    _u32.IsZoomed.restype = ctypes.c_bool
    _u32.IsZoomed.argtypes = [wt.HWND]
    _u32.GetSystemMetrics.restype = ctypes.c_int
    _u32.GetSystemMetrics.argtypes = [ctypes.c_int]

    SM_CXFRAME = 32
    SM_CYFRAME = 33
    SM_CXPADDEDBORDER = 92

    class MINMAXINFO(ctypes.Structure):
        _fields_ = [
            ("ptReserved", wt.POINT),
            ("ptMaxSize", wt.POINT),
            ("ptMaxPosition", wt.POINT),
            ("ptMinTrackSize", wt.POINT),
            ("ptMaxTrackSize", wt.POINT),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wt.DWORD),
            ("rcMonitor", wt.RECT),
            ("rcWork", wt.RECT),
            ("dwFlags", wt.DWORD),
        ]

    class NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [
            ("rgrc", wt.RECT * 3),
            ("lppos", ctypes.c_void_p),
        ]

    _u32.GetMonitorInfoW.argtypes = [wt.HANDLE, ctypes.POINTER(MONITORINFO)]

    # --- style: keep caption semantics, hide native chrome in WM_NCCALCSIZE --
    old_style = _u32.GetWindowLongW(hwnd, GWL_STYLE)
    new_style  = old_style | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MAXIMIZEBOX | WS_MINIMIZEBOX
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

    def _proc(h: int, msg: int, wp: int, lp: int) -> int:
        try:
            if msg == WM_GETMINMAXINFO:
                monitor = _u32.MonitorFromWindow(h, MONITOR_DEFAULTTONEAREST)
                if monitor:
                    info = MONITORINFO()
                    info.cbSize = ctypes.sizeof(MONITORINFO)
                    if _u32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                        mmi = ctypes.cast(lp, ctypes.POINTER(MINMAXINFO)).contents
                        work = info.rcWork
                        mon = info.rcMonitor
                        mmi.ptMaxPosition.x = int(work.left - mon.left)
                        mmi.ptMaxPosition.y = int(work.top - mon.top)
                        mmi.ptMaxSize.x = int(work.right - work.left)
                        mmi.ptMaxSize.y = int(work.bottom - work.top)
                        return 0

            if msg == WM_NCCALCSIZE and wp:
                # Borderless-maximized fix: when WS_THICKFRAME is set and we
                # collapse the non-client area, Windows still positions the
                # maximized window so the (invisible) frame extends past the
                # work area by SM_CXFRAME + SM_CXPADDEDBORDER on each side.
                # The client then includes those off-screen pixels and edge
                # content gets clipped. Snap the client rect to the monitor's
                # work area so nothing is lost.
                if _u32.IsZoomed(h):
                    try:
                        params = ctypes.cast(
                            lp, ctypes.POINTER(NCCALCSIZE_PARAMS)
                        ).contents
                        monitor = _u32.MonitorFromWindow(
                            h, MONITOR_DEFAULTTONEAREST
                        )
                        if monitor:
                            info = MONITORINFO()
                            info.cbSize = ctypes.sizeof(MONITORINFO)
                            if _u32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                                params.rgrc[0].left   = info.rcWork.left
                                params.rgrc[0].top    = info.rcWork.top
                                params.rgrc[0].right  = info.rcWork.right
                                params.rgrc[0].bottom = info.rcWork.bottom
                            else:
                                frame_x = _u32.GetSystemMetrics(SM_CXFRAME) + \
                                          _u32.GetSystemMetrics(SM_CXPADDEDBORDER)
                                frame_y = _u32.GetSystemMetrics(SM_CYFRAME) + \
                                          _u32.GetSystemMetrics(SM_CXPADDEDBORDER)
                                params.rgrc[0].left   += frame_x
                                params.rgrc[0].right  -= frame_x
                                params.rgrc[0].top    += frame_y
                                params.rgrc[0].bottom -= frame_y
                    except Exception as exc:
                        print(f"WM_NCCALCSIZE maximized inset failed: {exc}")
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
                return _u32.DefWindowProcW(h, msg, wp, lp)

            # Native drag-out trigger. ``post_native_drag`` enqueues paths and
            # PostMessageW's this message; we run the modal DoDragDrop on this
            # UI thread (which already owns the WebView's mouse capture) so it
            # never races Chromium's HTML5 drag. Mirrors what tauri-plugin-drag
            # does on Windows.
            if msg == WM_APP_DRAG:
                global _pending_drag_paths
                paths = list(_pending_drag_paths)
                _pending_drag_paths = []
                print(f"[symphony-drag] WndProc WM_APP_DRAG paths={paths}")
                if paths:
                    try:
                        start_file_drag(paths)
                    except Exception as exc:  # noqa: BLE001
                        print(f"[symphony-drag] WndProc DoDragDrop failed: {exc}")
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
