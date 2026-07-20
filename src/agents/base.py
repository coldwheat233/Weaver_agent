"""Agent 基类 —— 第 17 章解耦：依赖 LLMService 抽象而非 LiteLLM"""

import json
from typing import List, Dict, Optional, Any
from src.core.llm_service import LLMService
from src.utils.logging_config import logger


class BaseAgent:
    """所有 Agent 的基类。通过依赖注入接收 LLMService。"""

    def __init__(self, llm: LLMService, model: str = "",
                 temperature: float = 0.7, max_tokens: int = 4000, retry_count: int = 2):
        self.llm = llm
        if not model:
            from src.utils.config import get_settings
            model = get_settings().WEAVER_MODEL or "deepseek-chat"
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retry_count = retry_count

    async def call_llm(self, messages: List[Dict[str, str]],
                       response_format: Optional[dict] = None):
        """调用 LLM，带重试 + 追踪"""
        from src.utils.tracing import get_trace_id
        import time

        last_error = None
        trace_id = get_trace_id()
        for attempt in range(self.retry_count + 1):
            t0 = time.monotonic()
            try:
                resp = await self.llm.complete(
                    messages=messages,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format=response_format,
                )
                elapsed = (time.monotonic() - t0) * 1000
                logger.bind(component="base_agent", trace_id=trace_id).debug(
                    f"LLM call OK: model={self.model} tokens_in={resp.input_tokens} "
                    f"tokens_out={resp.output_tokens} latency={elapsed:.0f}ms "
                    f"cost=${resp.cost_usd:.4f}"
                )
                return resp
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt+1}/{self.retry_count+1} failed: {e}")
                if attempt < self.retry_count:
                    import asyncio
                    await asyncio.sleep(1 * (attempt + 1))
        raise last_error

    async def call_llm_json(self, messages: List[Dict[str, str]]) -> dict:
        """调用 LLM 并解析 JSON 响应，带降级"""
        messages.append({
            "role": "system",
            "content": "You MUST respond with valid JSON only. No markdown fences, no preamble."
        })
        resp = await self.call_llm(messages)
        content = resp.content.strip()

        # 移除可能的 markdown 代码块包裹
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:]) if len(lines) > 1 else content
            if content.endswith("```"):
                content = content[:-3].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 降级：尝试正则提取 JSON 对象
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to parse JSON from LLM response: {content[:500]}")
            return {"_parse_error": True, "_raw": content}
