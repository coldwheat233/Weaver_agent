"""运行时模型配置 —— ~/.weaver/config.json

优先级: config.json > .env > 内置默认 (DeepSeek)
热生效: 保存后立即生效, 无需重启
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


def user_data_root() -> Path:
    """用户级数据根目录 — 打包后程序目录不可写, 统一放这里"""
    root = Path.home() / ".weaver"
    root.mkdir(parents=True, exist_ok=True)
    return root


CONFIG_PATH = user_data_root() / "config.json"

# provider → 默认 base_url
PROVIDER_DEFAULTS: Dict[str, Dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com",
        "model": "gpt-4o-mini",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
    },
    "custom": {
        "base_url": "",
        "model": "",
    },
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "deepseek",
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "light_model": "deepseek-chat",
    "temperature": 0.7,
}


class RuntimeConfig:
    """运行时配置单例"""

    _cache: Optional[Dict[str, Any]] = None

    @classmethod
    def load(cls) -> Dict[str, Any]:
        """加载配置, 优先级: config.json > .env > 默认"""
        if cls._cache is not None:
            return cls._cache

        cfg = dict(DEFAULT_CONFIG)

        # 层 1: .env / 环境变量
        import os
        if os.environ.get("OPENAI_API_KEY"):
            cfg["api_key"] = os.environ["OPENAI_API_KEY"]
        if os.environ.get("OPENAI_API_BASE"):
            cfg["base_url"] = os.environ["OPENAI_API_BASE"]
        if os.environ.get("WEAVER_MODEL"):
            cfg["model"] = os.environ["WEAVER_MODEL"].replace("openai/", "")
        if os.environ.get("LIGHT_MODEL"):
            cfg["light_model"] = os.environ["LIGHT_MODEL"].replace("openai/", "")

        # 层 2: config.json (最高优先级)
        if CONFIG_PATH.exists():
            try:
                saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                for k in DEFAULT_CONFIG:
                    if k in saved and saved[k] != "":
                        cfg[k] = saved[k]
            except (json.JSONDecodeError, OSError):
                pass

        cls._cache = cfg
        return cfg

    @classmethod
    def save(cls, updates: Dict[str, Any]):
        """保存配置到 config.json 并热生效"""
        current = cls.load()
        current.update(updates)

        # provider 变化时自动填默认 base_url/model (除非用户显式给了)
        provider = current.get("provider", "deepseek")
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        if "base_url" not in updates and defaults.get("base_url"):
            current["base_url"] = defaults["base_url"]
        if "model" not in updates and defaults.get("model"):
            current["model"] = defaults["model"]

        CONFIG_PATH.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        cls._cache = current

    @classmethod
    def masked(cls) -> Dict[str, Any]:
        """返回脱敏配置 (api_key 只露尾 4 位)"""
        cfg = dict(cls.load())
        key = cfg.get("api_key", "")
        if key and len(key) > 4:
            cfg["api_key_masked"] = f"{key[:3]}...{key[-4:]}"
        elif key:
            cfg["api_key_masked"] = "已设置"
        else:
            cfg["api_key_masked"] = ""
        cfg["has_api_key"] = bool(key)
        cfg.pop("api_key", None)
        return cfg

    @classmethod
    def get_full_key(cls) -> str:
        """获取完整 API key (仅后端内部使用)"""
        return cls.load().get("api_key", "")

    @classmethod
    def get_base_url(cls) -> str:
        return cls.load().get("base_url", "https://api.deepseek.com")

    @classmethod
    def get_model(cls, light: bool = False) -> str:
        cfg = cls.load()
        return cfg.get("light_model" if light else "model", "deepseek-chat")
