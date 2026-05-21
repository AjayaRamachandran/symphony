// Symphony splash launcher.
//
// Boots a borderless Tauri window showing a static loading screen, spawns the
// Python pywebview backend as a child process, and hides the splash as soon as
// the backend prints ``__SYMPHONY_READY__`` to stdout. When the backend exits,
// the launcher exits with it.
//
// Output strategy: release builds use ``windows_subsystem = "windows"`` so a
// double-click does not pop a console window, but that also detaches the
// launcher from any parent terminal. To make crashes diagnosable we
//   1. ``AttachConsole(ATTACH_PARENT_PROCESS)`` on startup so a launch from a
//      shell sees stdout/stderr live, and
//   2. always tee log output to ``%LOCALAPPDATA%\Symphony\launcher.log`` (or
//      ``~/Library/Logs/Symphony/launcher.log`` on macOS), which is robust
//      across double-click launches and silent crashes.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::{create_dir_all, File, OpenOptions};
use std::io::{BufRead, BufReader, Read as _, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use std::thread;
use std::time::{Duration, Instant};

use tauri::Manager;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const READY_MARKER: &str = "__SYMPHONY_READY__";
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

// Windows AppUserModelID. Must match the `identifier` in tauri.conf.json and
// the IDs set by the Python backend (main.py) and the inner editor
// (inner/src/utils/platform_controller.py). The installer assigns this same
// ID to the Symphony Start Menu / Desktop shortcuts, so when every visible
// HWND across the launcher, pywebview backend, and pygame editor declares it
// explicitly, Windows groups them all under the installed `Symphony` shortcut
// and pinning from any surface pins the launcher, not a child binary.
#[cfg(windows)]
const APP_USER_MODEL_ID: &str = "com.ajayarsymphony.desktop";

struct BackendProcess(#[allow(dead_code)] Mutex<Option<Child>>);

// PID of the spawned Python backend. Captured at setup time so the
// single-instance callback can grant the backend foreground rights on
// Windows before asking it to refocus its pywebview HWND.
static BACKEND_PID: OnceLock<u32> = OnceLock::new();

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

static LAUNCHER_LOG: Mutex<Option<File>> = Mutex::new(None);

fn launcher_log_path() -> Option<PathBuf> {
    if cfg!(windows) {
        std::env::var_os("LOCALAPPDATA")
            .map(|p| PathBuf::from(p).join("Symphony").join("launcher.log"))
    } else if cfg!(target_os = "macos") {
        std::env::var_os("HOME").map(|p| {
            PathBuf::from(p)
                .join("Library")
                .join("Logs")
                .join("Symphony")
                .join("launcher.log")
        })
    } else {
        std::env::var_os("HOME").map(|p| {
            PathBuf::from(p)
                .join(".local")
                .join("share")
                .join("Symphony")
                .join("launcher.log")
        })
    }
}

fn open_launcher_log() -> Option<PathBuf> {
    let path = launcher_log_path()?;
    if let Some(parent) = path.parent() {
        let _ = create_dir_all(parent);
    }
    let file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .ok()?;
    if let Ok(mut guard) = LAUNCHER_LOG.lock() {
        *guard = Some(file);
    }
    Some(path)
}

fn log_line(msg: impl AsRef<str>) {
    let s = msg.as_ref();
    eprintln!("{}", s);
    if let Ok(mut guard) = LAUNCHER_LOG.lock() {
        if let Some(file) = guard.as_mut() {
            let _ = writeln!(file, "{}", s);
            let _ = file.flush();
        }
    }
}

fn install_panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        let location = info
            .location()
            .map(|l| format!("{}:{}", l.file(), l.line()))
            .unwrap_or_else(|| "<unknown>".to_string());
        let payload = info
            .payload()
            .downcast_ref::<&str>()
            .map(|s| (*s).to_string())
            .or_else(|| info.payload().downcast_ref::<String>().cloned())
            .unwrap_or_else(|| "<non-string payload>".to_string());
        log_line(format!(
            "[launcher] PANIC at {}: {}",
            location, payload
        ));
    }));
}

// ---------------------------------------------------------------------------
// Console attach (Windows only)
// ---------------------------------------------------------------------------

#[cfg(windows)]
fn try_attach_parent_console() {
    // Attach to the console of the launching process (CMD/PowerShell). If the
    // launcher was started by double-click there is no parent console and
    // AttachConsole returns 0; we ignore the failure and fall back to the
    // log file. After a successful attach Rust's std::io::stdout/stderr
    // resolve their handles lazily, so the first println! after this call
    // picks up the freshly-attached console output handle.
    extern "system" {
        fn AttachConsole(process_id: u32) -> i32;
    }
    const ATTACH_PARENT_PROCESS: u32 = 0xFFFF_FFFF;
    unsafe {
        let _ = AttachConsole(ATTACH_PARENT_PROCESS);
    }
}

#[cfg(not(windows))]
fn try_attach_parent_console() {}

// ---------------------------------------------------------------------------
// AppUserModelID (Windows only)
// ---------------------------------------------------------------------------

#[cfg(windows)]
fn set_app_user_model_id() {
    // SetCurrentProcessExplicitAppUserModelID binds this process (and every
    // top-level HWND it creates) to the same AUMID Tauri's NSIS installer
    // stamps onto the `Symphony` shortcut. Without this call, the splash
    // HWND would inherit the default AUMID derived from the executable
    // path, which makes the taskbar treat the launcher binary as a
    // separate app from the installed shortcut and breaks pinning.
    extern "system" {
        fn SetCurrentProcessExplicitAppUserModelID(app_id: *const u16) -> i32;
    }
    let wide: Vec<u16> = APP_USER_MODEL_ID
        .encode_utf16()
        .chain(std::iter::once(0))
        .collect();
    let hr = unsafe { SetCurrentProcessExplicitAppUserModelID(wide.as_ptr()) };
    if hr < 0 {
        log_line(format!(
            "[launcher] SetCurrentProcessExplicitAppUserModelID(\"{}\") failed: 0x{:08X}",
            APP_USER_MODEL_ID, hr as u32
        ));
    } else {
        log_line(format!(
            "[launcher] AppUserModelID set to {}",
            APP_USER_MODEL_ID
        ));
    }
}

#[cfg(not(windows))]
fn set_app_user_model_id() {}

// ---------------------------------------------------------------------------
// Child process helpers
// ---------------------------------------------------------------------------

#[cfg(windows)]
fn hide_child_console(command: &mut Command) {
    command.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(not(windows))]
fn hide_child_console(_command: &mut Command) {}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

fn main() {
    try_attach_parent_console();
    let log_path = open_launcher_log();
    install_panic_hook();
    set_app_user_model_id();

    log_line(format!(
        "[launcher] symphony-launcher v{} ({} build) starting",
        env!("CARGO_PKG_VERSION"),
        if cfg!(debug_assertions) { "debug" } else { "release" }
    ));
    if let Some(p) = &log_path {
        log_line(format!("[launcher] log file: {}", p.display()));
    } else {
        log_line("[launcher] WARNING: could not resolve a log file path");
    }

    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(run_launcher));
    match result {
        Ok(Ok(())) => {}
        Ok(Err(err)) => {
            log_line(format!("[launcher] fatal: {}", err));
            std::process::exit(1);
        }
        Err(_) => {
            // panic_hook already logged the details.
            std::process::exit(2);
        }
    }
}

fn run_launcher() -> Result<(), String> {
    tauri::Builder::default()
        // The single-instance plugin must be the first plugin registered so
        // its hidden message-loop window is in place before any other plugin
        // (or our setup hook) does work that depends on a single owner of
        // the user-data directory. When a duplicate Symphony.exe launches it
        // hands argv to this callback in the original process via WM_COPYDATA
        // (Windows) / equivalent IPC on other platforms, then exits.
        .plugin(tauri_plugin_single_instance::init(|_app, argv, _cwd| {
            handle_second_instance(argv);
        }))
        .setup(|app| {
            let handle = app.handle().clone();
            let mut child = match spawn_backend() {
                Ok(c) => c,
                Err(err) => {
                    log_line(format!("[launcher] failed to spawn backend: {}", err));
                    return Err(Box::new(err) as Box<dyn std::error::Error>);
                }
            };
            let _ = BACKEND_PID.set(child.id());

            // Capture stdout for the ready-marker watcher.
            let stdout = child
                .stdout
                .take()
                .ok_or("backend child has no stdout pipe")?;

            let watcher_handle = handle.clone();
            thread::spawn(move || {
                let reader = BufReader::new(stdout);
                for line in reader.lines().map_while(Result::ok) {
                    log_line(format!("[backend] {}", line));
                    if line.contains(READY_MARKER) {
                        if let Some(splash) = watcher_handle.get_webview_window("splash") {
                            let _ = splash.hide();
                        }
                    }
                }
                // Backend EOF -> assume exit -> tear down the launcher.
                log_line("[launcher] backend stdout closed; exiting");
                watcher_handle.exit(0);
            });

            // Stderr passthrough on a separate thread so the backend's logs
            // don't get lost.
            if let Some(stderr) = child.stderr.take() {
                thread::spawn(move || {
                    let reader = BufReader::new(stderr);
                    for line in reader.lines().map_while(Result::ok) {
                        log_line(format!("[backend err] {}", line));
                    }
                });
            }

            app.manage(BackendProcess(Mutex::new(Some(child))));
            Ok(())
        })
        .on_window_event(|_window, event| {
            // Swallow user close requests on the splash; we close it ourselves
            // when the backend signals ready.
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .map_err(|e| format!("tauri runtime error: {}", e))
}

// Scans the launcher's argv for a ``.symphony`` file path that exists on disk
// (the OS shell passes it as the first positional arg when the user opens a
// .symphony file from Explorer). Returns the canonical absolute path so the
// backend doesn't have to re-resolve relative or shell-quoted forms.
fn resolve_pending_open_file() -> Option<PathBuf> {
    for arg in std::env::args().skip(1) {
        if !arg.to_lowercase().ends_with(".symphony") {
            continue;
        }
        let raw = PathBuf::from(&arg);
        if !raw.exists() {
            log_line(format!(
                "[launcher] ignoring .symphony argv {:?}: path does not exist",
                arg
            ));
            continue;
        }
        match std::fs::canonicalize(&raw) {
            Ok(canon) => return Some(canon),
            Err(err) => {
                log_line(format!(
                    "[launcher] failed to canonicalize {:?}: {}",
                    arg, err
                ));
                return Some(raw);
            }
        }
    }
    None
}

// Strips Windows' ``\\?\`` extended-length prefix from canonicalized paths so
// the value we hand to the backend is a familiar shape (``C:\...``) for
// downstream display and shutil/os.path normalization.
fn strip_extended_length_prefix(path: PathBuf) -> PathBuf {
    if cfg!(windows) {
        if let Some(s) = path.to_str() {
            if let Some(stripped) = s.strip_prefix(r"\\?\") {
                return PathBuf::from(stripped);
            }
        }
    }
    path
}

fn apply_pending_open_file(command: &mut Command) {
    if let Some(path) = resolve_pending_open_file().map(strip_extended_length_prefix) {
        log_line(format!(
            "[launcher] forwarding SYMPHONY_OPEN_FILE={}",
            path.display()
        ));
        command.env("SYMPHONY_OPEN_FILE", path);
    }
}

// ---------------------------------------------------------------------------
// Second-instance handoff
// ---------------------------------------------------------------------------
//
// When the OS attempts to launch a second Symphony.exe (bare double-click or
// "Open With" on a .symphony file), tauri-plugin-single-instance routes the
// duplicate launcher's argv into ``handle_second_instance`` in the original
// launcher process. We translate that into a "focus and maybe open this
// file" message to the running Python backend over a localhost handoff port
// the backend wrote to disk on startup.

fn user_data_dir() -> Option<PathBuf> {
    if cfg!(windows) {
        std::env::var_os("LOCALAPPDATA").map(|p| PathBuf::from(p).join("Symphony"))
    } else if cfg!(target_os = "macos") {
        std::env::var_os("HOME").map(|p| {
            PathBuf::from(p)
                .join("Library")
                .join("Application Support")
                .join("Symphony")
        })
    } else {
        std::env::var_os("HOME")
            .map(|p| PathBuf::from(p).join(".local").join("share").join("Symphony"))
    }
}

fn pm_port_file() -> Option<PathBuf> {
    user_data_dir().map(|d| d.join("pm-port.txt"))
}

// Polls pm-port.txt for up to ~1 s. On the very first second-instance race
// (user double-clicks Symphony.exe twice within ~500 ms) the backend may not
// have finished its HTTP server bind yet.
fn read_pm_port_with_retry(deadline: Duration) -> Option<u16> {
    let path = pm_port_file()?;
    let started = Instant::now();
    loop {
        if let Ok(contents) = std::fs::read_to_string(&path) {
            if let Ok(port) = contents.trim().parse::<u16>() {
                if port != 0 {
                    return Some(port);
                }
            }
        }
        if started.elapsed() >= deadline {
            return None;
        }
        thread::sleep(Duration::from_millis(50));
    }
}

fn extract_symphony_path(argv: &[String]) -> Option<PathBuf> {
    for arg in argv.iter().skip(1) {
        if !arg.to_lowercase().ends_with(".symphony") {
            continue;
        }
        let raw = PathBuf::from(arg);
        if !raw.exists() {
            log_line(format!(
                "[launcher] second-instance: ignoring .symphony argv {:?}: missing",
                arg
            ));
            continue;
        }
        return Some(
            std::fs::canonicalize(&raw)
                .map(strip_extended_length_prefix)
                .unwrap_or(raw),
        );
    }
    None
}

#[cfg(windows)]
fn allow_backend_foreground() {
    let Some(pid) = BACKEND_PID.get().copied() else {
        return;
    };
    extern "system" {
        fn AllowSetForegroundWindow(process_id: u32) -> i32;
    }
    let ok = unsafe { AllowSetForegroundWindow(pid) };
    if ok == 0 {
        log_line(format!(
            "[launcher] AllowSetForegroundWindow({}) failed (last-error not fetched)",
            pid
        ));
    }
}

#[cfg(not(windows))]
fn allow_backend_foreground() {}

// Minimal 1-shot HTTP/1.1 POST so we don't pull in a full HTTP crate.
fn post_handoff(port: u16, body: &str) -> std::io::Result<()> {
    let mut stream = TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().map_err(|e| {
            std::io::Error::new(std::io::ErrorKind::InvalidInput, format!("addr: {}", e))
        })?,
        Duration::from_secs(2),
    )?;
    stream.set_read_timeout(Some(Duration::from_secs(2)))?;
    stream.set_write_timeout(Some(Duration::from_secs(2)))?;
    let request = format!(
        "POST /instance HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: application/json\r\nContent-Length: {len}\r\nConnection: close\r\n\r\n{body}",
        port = port,
        len = body.as_bytes().len(),
        body = body
    );
    stream.write_all(request.as_bytes())?;
    let mut buf = Vec::new();
    let _ = stream.read_to_end(&mut buf);
    Ok(())
}

fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

fn handle_second_instance(argv: Vec<String>) {
    log_line(format!(
        "[launcher] forwarding second-instance argv: {:?}",
        argv
    ));
    let path = extract_symphony_path(&argv);

    let Some(port) = read_pm_port_with_retry(Duration::from_millis(1000)) else {
        log_line(
            "[launcher] second-instance: pm-port.txt not available; cannot focus existing window"
                .to_string(),
        );
        return;
    };

    allow_backend_foreground();

    let body = match &path {
        Some(p) => format!("{{\"path\":\"{}\"}}", json_escape(&p.to_string_lossy())),
        None => "{\"path\":null}".to_string(),
    };

    match post_handoff(port, &body) {
        Ok(()) => log_line(format!(
            "[launcher] posted to PM handoff on port {} (path={:?})",
            port, path
        )),
        Err(err) => log_line(format!(
            "[launcher] PM handoff POST failed on port {}: {}",
            port, err
        )),
    }
}

#[cfg(debug_assertions)]
fn spawn_backend() -> std::io::Result<Child> {
    // Dev: run the python source directly from the repo root. The launcher's
    // working directory while ``tauri dev`` runs is ``src-tauri/`` so
    // ``../main.py`` resolves to the project root.
    let python = resolve_dev_python();
    let script = "../main.py";
    log_line(format!(
        "[launcher] dev mode: spawning {} -u {}",
        python.display(),
        script
    ));
    let mut command = Command::new(python);
    hide_child_console(&mut command);
    command
        .arg("-u")
        .arg(script)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    apply_pending_open_file(&mut command);
    command.spawn()
}

#[cfg(debug_assertions)]
fn resolve_dev_python() -> PathBuf {
    if let Some(path) = std::env::var_os("SYMPHONY_PYTHON") {
        return PathBuf::from(path);
    }

    let candidates = if cfg!(windows) {
        ["../venv/Scripts/python.exe", "../.venv/Scripts/python.exe"]
    } else {
        ["../venv/bin/python", "../.venv/bin/python"]
    };

    for candidate in candidates {
        let path = PathBuf::from(candidate);
        if path.exists() {
            return path;
        }
    }

    PathBuf::from(if cfg!(windows) { "python" } else { "python3" })
}

#[cfg(not(debug_assertions))]
fn spawn_backend() -> std::io::Result<Child> {
    // Release: the backend ships as a Tauri sidecar binary placed next to the
    // launcher executable. Tauri renames sidecars on-disk to include the
    // target triple, but at runtime they're invoked under the configured base
    // name (without the triple).
    let bin_name = if cfg!(windows) {
        "symphony-backend.exe"
    } else {
        "symphony-backend"
    };
    let exe_dir = std::env::current_exe()?
        .parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::NotFound, "exe has no parent"))?;

    let backend_path = exe_dir.join(bin_name);
    if !backend_path.exists() {
        log_line(format!(
            "[launcher] sidecar missing at {}",
            backend_path.display()
        ));
        return Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!(
                "symphony-backend sidecar missing at {}. Was `npm run stage:backend` run before `tauri build`?",
                backend_path.display()
            ),
        ));
    }

    log_line(format!(
        "[launcher] spawning backend sidecar: {}",
        backend_path.display()
    ));
    let mut command = Command::new(&backend_path);
    hide_child_console(&mut command);
    command.stdout(Stdio::piped()).stderr(Stdio::piped());
    apply_pending_open_file(&mut command);
    command.spawn()
}
