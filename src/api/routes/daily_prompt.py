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
    # 硬编码随机选领域——LLM 自己总是偏好分布式/缓存
    domains = ["数据结构与算法","编译原理","操作系统","计算机网络","数据库","AI/机器学习","信息安全","前端工程","DevOps","开源社区","软件工程与职业成长"]
    import random
    chosen = user_domains and random.random() < 0.4 and random.choice(user_domains) or random.choice(domains)

    resp = await llm.complete(
        messages=[{
            "role": "system",
            "content": f"你是技术导师。请为程序员出一个关于「{chosen}」领域的思考题。问题要开放、能引发讨论、没有标准答案。附带一句话说明为什么这个问题值得思考。输出JSON: {{\"question\":\"...\",\"context\":\"...\"}}。纯JSON不要其他文字。"
        }],
        temperature=1.0,
        max_tokens=200,
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
