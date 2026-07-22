"""每日技术思考题 —— 每天生成一个引发思考的技术问题

缓存: 每天只生成一次, 存储在 ~/.weaver/daily_prompt.json
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, date, timedelta
import json, asyncio
from src.utils.runtime_config import user_data_root

router = APIRouter(prefix="/api/daily-prompt", tags=["daily"])

PROMPT_CACHE = user_data_root() / "daily_prompt.json"


def _load_cache() -> dict:
    if PROMPT_CACHE.exists():
        try:
            return json.loads(PROMPT_CACHE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"date": "", "question": "", "context": ""}


def _save_cache(data: dict):
    PROMPT_CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def _generate_daily_question(user_domains: list[str] | None = None) -> dict:
    """用 LLM 生成一个今天的技术思考题"""
    from src.core.deepseek_service import OpenAICompatibleService

    domain_hint = ""
    if user_domains and len(user_domains) > 2:
        import random
        picks = random.sample(user_domains, min(3, len(user_domains)))
        domain_hint = f"用户关注的领域: {', '.join(picks)}。"

    llm = OpenAICompatibleService()
    resp = await llm.complete(
        messages=[{
            "role": "system",
            "content": f"""你是技术导师。每天给程序员出一个引发深度思考的技术问题。
规则:
1. 问题要开放、能引发讨论, 不要有标准答案
2. 涵盖: 系统设计、架构权衡、性能优化、代码质量、新技术趋势
3. 附带一句简短上下文说明这个问题为什么重要
4. 纯中文
{domain_hint}

输出 JSON:
{{"question": "...", "context": "为什么这个问题值得思考"}}"""
        }],
        temperature=0.9,
        max_tokens=300,
    )
    try:
        import re
        match = re.search(r'\{.*\}', resp.content, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"question": resp.content.strip()[:200], "context": ""}


@router.get("")
async def get_daily_prompt():
    """获取今日思考题 (缓存一天)"""
    cache = _load_cache()
    today = date.today().isoformat()

    if cache.get("date") == today and cache.get("question"):
        return cache

    # 尝试读取用户画像生成个性化问题
    user_domains = None
    try:
        from src.storage.database import get_async_session
        from sqlalchemy import text
        async with await get_async_session() as db:
            result = await db.execute(text("SELECT frequent_domains FROM user_profile WHERE id = 1"))
            row = result.fetchone()
            if row:
                user_domains = json.loads(row[0] or "[]")
    except Exception:
        pass

    data = await _generate_daily_question(user_domains)
    data["date"] = today
    _save_cache(data)
    return data


@router.post("/refresh")
async def refresh_daily_prompt():
    """强制刷新今日思考题"""
    PROMPT_CACHE.unlink(missing_ok=True)
    return await get_daily_prompt()
