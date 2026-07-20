"""结构化日志配置 —— loguru"""

import sys
from pathlib import Path
from loguru import logger as _logger

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{message}"
)


def setup_logging(log_level: str = "info"):
    _logger.remove()

    # 控制台
    _logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=log_level.upper(),
        colorize=True,
    )

    # 文件（如果 data/logs 存在）
    log_dir = Path("data/logs")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        _logger.add(
            log_dir / "weaver_{time:YYYY-MM-DD}.log",
            format=LOG_FORMAT,
            level="INFO",
            rotation="00:00",
            retention="30 days",
            compression="gz",
        )
        _logger.add(
            log_dir / "errors_{time:YYYY-MM-DD}.log",
            format=LOG_FORMAT,
            level="ERROR",
            rotation="00:00",
            retention="90 days",
        )
    except Exception:
        pass  # FC 环境可能没有写权限，仅控制台输出

    return _logger


logger = _logger
