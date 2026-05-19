// Symphony splash launcher.
//
// Boots a borderless Tauri window showing a static loading screen, spawns the
// Python pywebview backend as a child process, and hides the splash as soon as
// the backend prints ``__SYMPHONY_READY__`` to stdout. When the backend exits,
// the launcher exits with it.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
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

#[cfg(windows)]
fn hide_child_console(command: &mut Command) {
    command.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(not(windows))]
fn hide_child_console(_command: &mut Command) {}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let handle = app.handle().clone();
            let mut child = spawn_backend()?;

            // Capture stdout for the ready-marker watcher.
            let stdout = child
                .stdout
                .take()
                .expect("backend child has no stdout pipe");

            let watcher_handle = handle.clone();
            thread::spawn(move || {
                let reader = BufReader::new(stdout);
                for line in reader.lines().map_while(Result::ok) {
                    println!("[backend] {}", line);
                    if line.contains(READY_MARKER) {
                        if let Some(splash) = watcher_handle.get_webview_window("splash") {
                            let _ = splash.hide();
                        }
                    }
                }
                // Backend EOF -> assume exit -> tear down the launcher.
                watcher_handle.exit(0);
            });

            // Optional: stderr passthrough on a separate thread so the
            // backend's logs don't get lost.
            if let Some(stderr) = child.stderr.take() {
                thread::spawn(move || {
                    let reader = BufReader::new(stderr);
                    for line in reader.lines().map_while(Result::ok) {
                        eprintln!("[backend err] {}", line);
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
        .expect("error while running symphony launcher");
}

#[cfg(debug_assertions)]
fn spawn_backend() -> std::io::Result<Child> {
    // Dev: run the python source directly from the repo root.
    let python = if cfg!(windows) { "python" } else { "python3" };
    let mut command = Command::new(python);
    hide_child_console(&mut command);
    command
        .arg("-u")
        .arg("../main.py")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    command.spawn()
}

#[cfg(not(debug_assertions))]
fn spawn_backend() -> std::io::Result<Child> {
    // Release: the backend ships as a Tauri sidecar binary placed next to the
    // launcher executable. Tauri renames sidecars on-disk to include the
    // target triple, but at runtime they're invoked under the configured base
    // name.
    let bin_name = if cfg!(windows) {
        "symphony-backend.exe"
    } else {
        "symphony-backend"
    };
    let exe_dir = std::env::current_exe()?
        .parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| {
            std::io::Error::new(std::io::ErrorKind::NotFound, "exe has no parent")
        })?;

    let mut command = Command::new(exe_dir.join(bin_name));
    hide_child_console(&mut command);
    command.stdout(Stdio::piped()).stderr(Stdio::piped());
    command.spawn()
}
