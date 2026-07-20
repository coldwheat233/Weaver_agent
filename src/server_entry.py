"""PyInstaller 专用入口 — 仅启动 uvicorn, 不碰桌面组件

直接 import app (而非字符串引用), 让 PyInstaller 追踪到所有 src 模块
"""

import sys
import os
import uvicorn
from src.api.server import app

if __name__ == "__main__":
    # 无终端环境 (Tauri sidecar) 下 stderr/stdout 可能为 None, 重定向到 devnull
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8765,
        log_level="error",
        # 无终端时用简单格式, 避免 isatty() 崩溃
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "simple": {
                    "format": "%(asctime)s | %(levelname)-8s | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "simple",
                    "stream": "ext://sys.stderr",
                },
            },
            "root": {"level": "ERROR", "handlers": ["console"]},
        },
    )
