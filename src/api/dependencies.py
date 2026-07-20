"""FastAPI 依赖注入"""

from src.utils.config import get_settings


def get_settings_dep():
    return get_settings()
