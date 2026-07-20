"""Idea Weaver —— 入口"""

import sys, time, os, socket
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_settings
from src.utils.logging_config import setup_logging


def _find_free_port(start=8765):
    """找可用端口"""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return start


def main():
    settings = get_settings()
    logger = setup_logging(settings.LOG_LEVEL)
    mode = sys.argv[1] if len(sys.argv) > 1 else settings.DEPLOY_MODE
    logger.info(f"Idea Weaver starting (mode={mode})")

    if mode == "desktop":
        _run_desktop(settings)
    else:
        _run_server_only(settings)


def _run_desktop(settings):
    """桌面模式"""
    import threading

    # 找空闲端口
    port = _find_free_port(settings.WEAVER_PORT)
    if port != settings.WEAVER_PORT:
        print(f"  端口 {settings.WEAVER_PORT} 被占用, 使用 {port}")
    settings.WEAVER_PORT = port

    # 1. 启动 API
    _start_api_server(settings, port)
    time.sleep(3)

    print(f"""
  ╔══════════════════════════════════════╗
  ║       Idea Weaver 已启动             ║
  ╠══════════════════════════════════════╣
  ║  Ctrl+Alt+[:  输入想法               ║
  ║  Ctrl+Alt+]:  用户后台               ║
  ║  Ctrl+C:      退出                    ║
  ║                                      ║
  ║  浏览器: http://localhost:{port}/ui/capture ║
  ╚══════════════════════════════════════╝
""")

    # 2. 注册双热键
    from src.ui.overlay_window import CaptureOverlay
    overlay = CaptureOverlay()
    overlay.set_port(port)

    from src.ui.hotkey_listener import HotkeyListener
    hl = HotkeyListener(
        on_input=lambda: overlay.show_input(),
        on_output=lambda: overlay.show_output(),
    )
    hl.start()
    print(f"  [OK] Ctrl+Alt+[ → 输入  |  Ctrl+Alt+] → 后台")

    # 3. 系统托盘
    try:
        _start_tray(port)
    except Exception as e:
        print(f"  [!] 托盘启动失败: {e}")

    # 4. V3 后台监控
    _start_v3_background_monitor(port)

    # 5. 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  正在退出...")
        hl.stop()


def _start_tray(port: int):
    """系统托盘图标"""
    import pystray, webbrowser
    from PIL import Image, ImageDraw

    # 画一个简单的青色圆形图标
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill="#0891B2")
    draw.text((22, 16), "W", fill="white")

    def on_open(icon, item):
        webbrowser.open(f"http://localhost:{port}/dashboard")

    def on_quit(icon, item):
        icon.stop()
        import os; os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("📊 用户后台", on_open, default=True),
        pystray.MenuItem("✏️ 输入想法", lambda: webbrowser.open(f"http://localhost:{port}/ui/capture")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ 退出", on_quit),
    )
    icon = pystray.Icon("idea_weaver", img, "Idea Weaver", menu)

    import threading
    t = threading.Thread(target=icon.run, daemon=True)
    t.start()
    return icon


def _start_v3_background_monitor(port: int):
    """V3: 后台定期扫描临界质量 + 自动提案"""
    import threading, httpx

    def _monitor_loop():
        while True:
            time.sleep(300)  # 每 5 分钟
            try:
                httpx.post(f"http://localhost:{port}/api/v3/scan-and-propose", timeout=30)
            except Exception:
                pass

    t = threading.Thread(target=_monitor_loop, daemon=True)
    t.start()


def _show_overlay_safe(overlay):
    """安全显示浮窗"""
    try:
        overlay.show()
    except Exception as e:
        print(f"  [!!] 浮窗不可用: {e}")


def _run_server_only(settings):
    """仅 API 服务"""
    from src.storage.database import init_db
    import asyncio
    async def _init():
        await init_db()
    asyncio.run(_init())

    import uvicorn
    uvicorn.run(
        "src.api.server:app", host="127.0.0.1", port=settings.WEAVER_PORT,
        workers=1, log_level=settings.LOG_LEVEL,
    )


def _start_api_server(settings, port=None):
    """后台线程启动 FastAPI"""
    import uvicorn, threading, asyncio
    p = port or settings.WEAVER_PORT

    def _run():
        async def _init():
            from src.storage.database import init_db
            await init_db()
        asyncio.run(_init())
        uvicorn.run(
            "src.api.server:app", host="127.0.0.1", port=p,
            workers=1, log_level="warning",
        )
    t = threading.Thread(target=_run, daemon=True)
    t.start()


if __name__ == "__main__":
    main()
