"""应用配置 —— pydantic-settings 管理，支持 .env + 环境变量覆盖"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置单例"""

    # === 部署模式 ===
    DEPLOY_MODE: str = "desktop"  # "desktop" | "docker" | "fc"

    # === LLM ===
    LLM_PROVIDER: str = "litellm"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""
    VOYAGE_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    WEAVER_MODEL: str = "deepseek-chat"
    LIGHT_MODEL: str = "deepseek-chat"

    # === 运行时 ===
    WEAVER_PORT: int = 8765
    LOG_LEVEL: str = "info"
    WEAVER_MAX_ITERATIONS: int = 3

    # === 路径（按部署模式自适应）===
    @property
    def data_dir(self) -> Path:
        if self.DEPLOY_MODE == "fc":
            return Path(os.environ.get("DATA_DIR", "/mnt/auto/weaver/data"))
        if self.DEPLOY_MODE == "docker":
            return Path("/home/weaver/app/data")
        # desktop: 用户级目录 — 打包后程序目录不可写
        from src.utils.runtime_config import user_data_root
        return user_data_root() / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "weaver.db"

    @property
    def checkpoint_db_path(self) -> Path:
        return self.data_dir / "weaver_checkpoints.db"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def assets_dir(self) -> Path:
        return self.data_dir / "assets"

    @property
    def exports_dir(self) -> Path:
        from src.utils.runtime_config import user_data_root
        return user_data_root() / "exports"

    @property
    def use_async_weave(self) -> bool:
        """FC 模式用异步编织"""
        return self.DEPLOY_MODE == "fc"

    @property
    def api_port(self) -> int:
        """FC 要求 9000，其余用配置值"""
        if self.DEPLOY_MODE == "fc":
            return int(os.environ.get("PORT", 9000))
        return self.WEAVER_PORT

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
