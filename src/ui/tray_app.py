"""系统托盘图标与菜单"""

import threading
import pystray
from PIL import Image, ImageDraw
from src.utils.logging_config import logger


def create_tray_icon(on_show_overlay, on_quit):
    """创建系统托盘图标"""

    # 绘制简易图标：青色圆形 + "W" 字母
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill="#0891B2")
    draw.text((22, 16), "W", fill="#FFFFFF")

    menu = pystray.Menu(
        pystray.MenuItem("✨ 捕捉想法", on_show_overlay, default=True),
        pystray.MenuItem("📋 查看最近设计", lambda: None),  # TODO
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ 退出", on_quit),
    )

    icon = pystray.Icon("idea_weaver", img, "Idea Weaver", menu)
    return icon


def run_tray(on_show_overlay, on_quit):
    """在独立线程中运行系统托盘"""
    icon = create_tray_icon(on_show_overlay, on_quit)

    def _run():
        icon.run()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("System tray started")
    return icon
