"""技术资讯聚合 —— RSS 源抓取

来源: Hacker News, Reddit programming, 知乎热榜, etc.
缓存 1 小时
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
import json, httpx, asyncio
from src.utils.runtime_config import user_data_root

router = APIRouter(prefix="/api/tech-news", tags=["news"])

CACHE_PATH = user_data_root() / "tech_news_cache.json"

# RSS 源
SOURCES = [
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage?count=8",
        "type": "rss",
    },
    {
        "name": "Reddit r/programming",
        "url": "https://www.reddit.com/r/programming/.rss",
        "type": "rss",
    },
    {
        "name": "GitHub Trending",
        "url": "https://github.com/trending/python?since=daily",
        "type": "html",
    },
]


def _load_cache() -> dict | None:
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            age = (datetime.utcnow() - datetime.fromisoformat(data["fetched_at"])).total_seconds()
            if age < 3600:  # 1 小时缓存
                return data
        except Exception:
            pass
    return None


def _save_cache(data: dict):
    CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def _fetch_rss(url: str, limit: int = 5) -> list[dict]:
    """抓取 RSS 源"""
    try:
        import xml.etree.ElementTree as ET
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"User-Agent": "IdeaWeaver/1.0"})
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        items = []
        for item in root.iter("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            # 去掉 HTML 标签
            import re
            desc = re.sub(r"<[^>]+>", "", desc)[:300]
            items.append({"title": title, "link": link, "description": desc})
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        return [{"title": f"抓取失败: {str(e)[:80]}", "link": "", "description": ""}]


async def _scrape_github_trending(url: str) -> list[dict]:
    """抓取 GitHub Trending 页面"""
    try:
        import re
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"User-Agent": "IdeaWeaver/1.0"})
            resp.raise_for_status()
        # 提取 repo 名称
        repos = re.findall(r'/trending/[^"]+?/([^/"]+)"', resp.text)
        descs = re.findall(r'<p class="col-9 color-fg-muted my-1 pr-4">\s*(.+?)\s*</p>', resp.text, re.DOTALL)
        items = []
        for i in range(min(5, len(repos))):
            items.append({
                "title": f"🔥 {repos[i]}",
                "link": f"https://github.com/{repos[i]}" if "/" not in repos[i] else f"https://github.com/trending/{repos[i]}",
                "description": descs[i].strip() if i < len(descs) else "",
            })
        return items
    except Exception as e:
        return [{"title": f"抓取失败: {str(e)[:80]}", "link": "", "description": ""}]


@router.get("")
async def get_tech_news():
    """获取最新技术新闻"""
    cached = _load_cache()
    if cached:
        return cached

    all_items = []
    for src in SOURCES:
        if src["type"] == "rss":
            items = await _fetch_rss(src["url"])
            for item in items:
                item["source"] = src["name"]
            all_items.extend(items)
        elif src["type"] == "html":
            items = await _scrape_github_trending(src["url"])
            for item in items:
                item["source"] = src["name"]
            all_items.extend(items)

    data = {
        "items": all_items,
        "fetched_at": datetime.utcnow().isoformat(),
        "count": len(all_items),
    }
    _save_cache(data)
    return data


@router.post("/refresh")
async def refresh_news():
    """强制刷新资讯"""
    CACHE_PATH.unlink(missing_ok=True)
    return await get_tech_news()


@router.post("/ingest")
async def ingest_as_idea(item: dict):
    """将一篇资讯文章作为想法摄入"""
    from src.storage.database import get_async_session
    from src.storage.idea_repo import IdeaRepo
    from src.core.models import IdeaNode, SourceType
    from src.agents.collector import CollectorAgent
    from src.core.deepseek_service import OpenAICompatibleService

    title = item.get("title", "")
    desc = item.get("description", "")
    source = item.get("source", "")
    content = f"[{source}] {title}"
    if desc:
        content += f" — {desc}"

    llm = OpenAICompatibleService()
    collector = CollectorAgent(llm)
    node = await collector.process(content, SourceType.TEXT)

    async with await get_async_session() as db:
        await IdeaRepo(db).create(node)

    return {"ok": True, "idea_id": str(node.id), "title": title}
