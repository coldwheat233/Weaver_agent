"""LLM 服务抽象 —— 第 17 章耦合分析解耦方案

Agent 不直接依赖 LiteLLM。通过此抽象解耦，测试可注入 FakeLLMService。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    content: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class LLMService(ABC):
    """与 LLM 供应商无关的抽象接口"""

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-5",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        ...


class LiteLLMService(LLMService):
    """基于 LiteLLM 的实现"""

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-5",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        import time
        import litellm

        start = time.monotonic()
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format

        resp = await litellm.acompletion(**kwargs)

        elapsed = (time.monotonic() - start) * 1000
        content = resp.choices[0].message.content or ""

        usage = resp.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        # cost 估算（LiteLLM 内置）
        try:
            cost_usd = litellm.cost_calculator.completion_cost(resp)
        except Exception:
            cost_usd = 0.0

        return LLMResponse(
            content=content,
            model=resp.model or model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=elapsed,
        )


class FakeLLMService(LLMService):
    """测试用假 LLM 服务，返回预设响应"""

    def __init__(self, canned_responses: List[str] | None = None):
        self.responses = canned_responses or ["{}"]
        self.call_count = 0
        self.calls: List[dict] = []

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "model": model})
        resp = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return LLMResponse(content=resp, model="fake", cost_usd=0.0, latency_ms=1.0)
