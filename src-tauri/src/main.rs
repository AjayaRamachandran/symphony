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
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;

use tauri::Manager;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const READY_MARKER: &str = "__SYMPHONY_READY__";
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

struct BackendProcess(#[allow(dead_code)] Mutex<Option<Child>>);

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
        .setup(|app| {
            let handle = app.handle().clone();
            let mut child = match spawn_backend() {
                Ok(c) => c,
                Err(err) => {
                    log_line(format!("[launcher] failed to spawn backend: {}", err));
                    return Err(Box::new(err) as Box<dyn std::error::Error>);
                }
            };

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

#[cfg(debug_assertions)]
fn spawn_backend() -> std::io::Result<Child> {
    // Dev: run the python source directly from the repo root. The launcher's
    // working directory while ``tauri dev`` runs is ``src-tauri/`` so
    // ``../main.py`` resolves to the project root.
    let python = if cfg!(windows) { "python" } else { "python3" };
    let script = "../main.py";
    log_line(format!(
        "[launcher] dev mode: spawning {} -u {}",
        python, script
    ));
    let mut command = Command::new(python);
    hide_child_console(&mut command);
    command
        .arg("-u")
        .arg(script)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    command.spawn()
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
    command.spawn()
}
