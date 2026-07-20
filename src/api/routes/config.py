"""模型配置路由 —— 配置器后端"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from src.utils.runtime_config import RuntimeConfig, PROVIDER_DEFAULTS

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    light_model: Optional[str] = None
    temperature: Optional[float] = None


@router.get("")
async def get_config():
    """获取当前配置 (api_key 脱敏)"""
    cfg = RuntimeConfig.masked()
    cfg["providers"] = [
        {"id": pid, "base_url": d["base_url"], "default_model": d["model"]}
        for pid, d in PROVIDER_DEFAULTS.items()
    ]
    return cfg


@router.put("")
async def update_config(update: ConfigUpdate):
    """保存配置并热生效"""
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    if not updates:
        return {"ok": False, "error": "no fields to update"}
    RuntimeConfig.save(updates)
    return {"ok": True, "config": RuntimeConfig.masked()}


@router.post("/test")
async def test_config(update: ConfigUpdate = ConfigUpdate()):
    """测试连接 — 用当前或传入的配置发 ping 请求"""
    import httpx, time
    from src.utils.runtime_config import RuntimeConfig as RC

    cfg = dict(RC.load())
    pending = {k: v for k, v in update.model_dump().items() if v is not None}
    cfg.update(pending)

    if not cfg.get("api_key") and cfg.get("provider") != "ollama":
        return {"ok": False, "error": "API Key 未设置"}

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            headers = {"Content-Type": "application/json"}
            if cfg.get("api_key"):
                headers["Authorization"] = f"Bearer {cfg['api_key']}"
            resp = await client.post(
                f"{cfg['base_url']}/v1/chat/completions",
                headers=headers,
                json={
                    "model": cfg.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
            )
        latency = (time.monotonic() - t0) * 1000
        if resp.status_code == 200:
            return {"ok": True, "latency_ms": round(latency), "model": cfg["model"]}
        return {
            "ok": False,
            "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
