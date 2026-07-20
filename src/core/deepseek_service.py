"""OpenAI 兼容 LLM 服务 —— 支持 DeepSeek / OpenAI / Ollama / 自定义

配置来源: src/utils/runtime_config.py (~/.weaver/config.json)
协议: OpenAI Chat Completions (所有供应商通用)
"""

from typing import List, Dict, Optional
import httpx
import time
from src.core.llm_service import LLMService, LLMResponse
from src.utils.logging_config import logger
from src.utils.runtime_config import RuntimeConfig


class OpenAICompatibleService(LLMService):
    """按 runtime_config 调用任意 OpenAI 兼容 API"""

    def __init__(self, api_key: str = "", base_url: str = ""):
        # 显式参数优先, 否则读 runtime_config
        self.api_key = api_key or RuntimeConfig.get_full_key()
        self.base_url = base_url or RuntimeConfig.get_base_url()

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        t0 = time.monotonic()
        # 模型: 参数 > runtime_config, 去掉 openai/ 前缀
        clean_model = (model or RuntimeConfig.get_model()).replace("openai/", "")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": clean_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if resp.status_code >= 400:
                logger.error(f"LLM {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()

            elapsed = (time.monotonic() - t0) * 1000
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", clean_model),
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                cost_usd=0.0,
                latency_ms=elapsed,
            )
        except Exception as e:
            logger.error(f"LLM API error ({self.base_url}): {e}")
            raise


# 向后兼容别名 — 已有代码 import DeepSeekService 不破坏
DeepSeekService = OpenAICompatibleService
