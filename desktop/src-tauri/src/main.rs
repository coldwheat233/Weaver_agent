#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Child};
use std::sync::Mutex;
use tauri::Manager;
use tauri::menu::{MenuBuilder, MenuItemBuilder};
use tauri::tray::{TrayIconBuilder, MouseButton, MouseButtonState, TrayIconEvent};
use tauri::image::Image;
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut};

struct PythonBackend(Mutex<Option<Child>>);

const TRAY_ICON: &[u8] = include_bytes!("../icons/icon-32.rgba");

fn find_weave_root() -> Option<std::path::PathBuf> {
    // tauri dev: cwd = desktop/src-tauri → WEAVE root = ../..
    // run.py:    cwd = WEAVE root      → WEAVE root = .
    let candidates = [".", "..", "../..", "../../.."];
    for cand in candidates {
        let p = std::path::Path::new(cand).join("src").join("api").join("server.py");
        if p.exists() {
            return Some(std::path::PathBuf::from(cand));
        }
    }
    // 兜底：环境变量指定
    std::env::var("WEAVE_ROOT").ok().map(std::path::PathBuf::from)
}

fn port_in_use(port: u16) -> bool {
    std::net::TcpListener::bind(("127.0.0.1", port)).is_err()
}

fn start_python_backend() -> Option<Child> {
    if port_in_use(8765) {
        println!("Python backend already running on port 8765, skipping spawn");
        return None;
    }

    // 优先: sidecar (Tauri externalBin 打包后文件名含平台后缀, 匹配 weaver-backend*.exe)
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(dir) = exe_path.parent() {
            if let Ok(entries) = std::fs::read_dir(dir) {
                for entry in entries.flatten() {
                    let name = entry.file_name().to_string_lossy().to_string();
                    if name.starts_with("weaver-backend") && name.ends_with(".exe") {
                        let path = entry.path();
                        println!("Found backend sidecar: {:?}", path);
                        match Command::new(&path).spawn() {
                            Ok(child) => {
                                println!("Backend sidecar spawned (pid {})", child.id());
                                return Some(child);
                            }
                            Err(e) => eprintln!("ERROR: sidecar spawn failed: {}", e),
                        }
                        break;
                    }
                }
            }
        }
    }

    // 回退: 开发模式 (find_weave_root + python -m uvicorn)
    let root = match find_weave_root() {
        Some(r) => r,
        None => {
            eprintln!("ERROR: cannot locate WEAVE root (src/api/server.py not found)");
            return None;
        }
    };

    println!("Starting Python backend from {:?}", root);
    match Command::new("python")
        .args(["-m", "uvicorn", "src.api.server:app",
               "--host", "127.0.0.1", "--port", "8765", "--log-level", "error"])
        .current_dir(&root)
        .spawn()
    {
        Ok(child) => {
            println!("Python backend spawned (pid {})", child.id());
            Some(child)
        }
        Err(e) => {
            eprintln!("ERROR: failed to spawn python backend: {}", e);
            None
        }
    }
}

fn main() {
    let backend = start_python_backend();

    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .manage(PythonBackend(Mutex::new(backend)))
        .setup(|app| {
            let handle = app.handle().clone();

            // ── Global Shortcuts ──
            let h_input = handle.clone();
            app.global_shortcut().on_shortcut(
                Shortcut::new(Some(Modifiers::CONTROL | Modifiers::ALT), Code::BracketLeft),
                move |_app, _sc, _event| {
                    if let Some(w) = h_input.get_webview_window("input") {
                        let _ = w.unminimize();
                        let _ = w.show();
                        let _ = w.set_focus();
                    }
                },
            )?;

            let h_dash = handle.clone();
            app.global_shortcut().on_shortcut(
                Shortcut::new(Some(Modifiers::CONTROL | Modifiers::ALT), Code::BracketRight),
                move |_app, _sc, _event| {
                    if let Some(w) = h_dash.get_webview_window("dashboard") {
                        let _ = w.unminimize();
                        let _ = w.show();
                        let _ = w.set_focus();
                    }
                },
            )?;

            // ── System Tray ──
            let show_input = MenuItemBuilder::with_id("show_input", "✏️ 输入想法 (Ctrl+Alt+[)").build(app)?;
            let show_dash = MenuItemBuilder::with_id("show_dashboard", "📊 用户后台 (Ctrl+Alt+])").build(app)?;
            let quit = MenuItemBuilder::with_id("quit", "❌ 退出").build(app)?;
            let menu = MenuBuilder::new(app)
                .item(&show_input).item(&show_dash).separator().item(&quit)
                .build()?;

            let tray_icon = Image::new_owned(TRAY_ICON.to_vec(), 32, 32);

            let h_menu = handle.clone();
            TrayIconBuilder::new()
                .icon(tray_icon)
                .icon_as_template(false)
                .menu(&menu)
                .on_menu_event(move |app, event| match event.id().as_ref() {
                    "show_input" => {
                        if let Some(w) = app.get_webview_window("input") {
                            let _ = w.show(); let _ = w.set_focus();
                        }
                    }
                    "show_dashboard" => {
                        if let Some(w) = app.get_webview_window("dashboard") {
                            let _ = w.show(); let _ = w.set_focus();
                        }
                    }
                    "quit" => {
                        if let Ok(mut g) = app.state::<PythonBackend>().0.lock() {
                            if let Some(ref mut c) = *g { let _ = c.kill(); }
                        }
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(move |_tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left, button_state: MouseButtonState::Up, ..
                    } = event {
                        if let Some(w) = h_menu.get_webview_window("dashboard") {
                            match w.is_visible() {
                                Ok(true) => { let _ = w.hide(); }
                                Ok(false) => {
                                    let _ = w.unminimize();
                                    let _ = w.show();
                                    let _ = w.set_focus();
                                }
                                _ => {}
                            }
                        }
                    }
                })
                .build(app)?;

            println!("Idea Weaver ready. Ctrl+Alt+[ = input, Ctrl+Alt+] = dashboard");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Tauri error");
}
