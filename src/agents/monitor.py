"""Monitor Agent (V3) —— 持续监听外部信息源

定期扫描外部数据（RSS、文档），将新信息编织进现有想法图谱。
当某个概念簇达到临界质量时，自动触发设计提案。
"""

import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import IdeaNode, SourceType, ConceptCluster
from src.storage.database import get_async_session
from src.storage.idea_repo import IdeaRepo
from src.storage.vector_store import VectorStore
from src.core.embeddings import EmbeddingService
from src.utils.logging_config import logger
from src.utils.config import get_settings

settings = get_settings()

MONITOR_SYSTEM = """你是 Idea Weaver V3 的 Monitor Agent。
你接收一段外部文本（新闻、文档、API 数据），判断：
1. 是否与用户已有的想法图谱相关？
2. 如果是，提取核心洞见为标准化想法节点
3. 如果否，返回 skip

输出 JSON：
{
  "relevant": true/false,
  "standardized_content": "如相关，输出标准化想法描述",
  "relevance_reason": "为什么相关或不相关",
  "intent_tags": ["observation"|"insight"|"risk"|"opportunity"],
  "context_tags": ["领域关键词"]
}"""


class MonitorAgent:
    """外部信息监听者"""

    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(
            llm=llm,
            model="",
            temperature=0.3,
            max_tokens=1000,
        )
        self.embedding_service = EmbeddingService()

    async def ingest_external(self, content: str, source: str,
                              existing_embeddings: Optional[List[dict]] = None) -> Optional[IdeaNode]:
        """接收外部信息，判定相关性后决定是否纳入图谱"""
        messages = [
            {"role": "system", "content": MONITOR_SYSTEM},
            {"role": "user", "content": f"来源：{source}\n\n内容：{content[:3000]}"},
        ]

        data = await self.agent.call_llm_json(messages)

        if data.get("_parse_error") or not data.get("relevant"):
            logger.debug(f"Monitor: irrelevant content from {source}")
            return None

        node = IdeaNode(
            source_type=SourceType.TEXT,
            raw_content=content[:1000],
            standardized_content=data.get("standardized_content", content[:500]),
            intent_tags=data.get("intent_tags", ["observation"]),
            context_tags=data.get("context_tags", []),
            relevance_score=0.7,
            completeness_score=0.6,
            actionability_score=0.5,
            north_star_relevance=0.6,
        )

        logger.bind(component="monitor").info(
            f"Ingested external idea: {node.id} from {source}"
        )
        return node


class ExternalSourcePoller:
    """定期轮询外部数据源"""

    def __init__(self, monitor: MonitorAgent):
        self.monitor = monitor
        self._sources: List[dict] = []
        self._paused = False
        self._last_poll: dict[str, datetime] = {}

    def add_source(self, name: str, url: str, source_type: str = "rss",
                   poll_interval_minutes: int = 60):
        """添加监控源"""
        self._sources.append({
            "name": name,
            "url": url,
            "type": source_type,
            "interval": poll_interval_minutes,
        })
        logger.info(f"Added monitor source: {name} ({source_type})")

    def remove_source(self, name: str):
        self._sources = [s for s in self._sources if s["name"] != name]

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    async def poll_all(self) -> List[IdeaNode]:
        """轮询所有源，返回新摄入的想法"""
        if self._paused:
            return []

        new_nodes = []
        now = datetime.utcnow()

        for source in self._sources:
            last = self._last_poll.get(source["name"])
            if last and (now - last) < timedelta(minutes=source["interval"]):
                continue  # 还没到轮询间隔

            try:
                content = await self._fetch_source(source)
                if content:
                    node = await self.monitor.ingest_external(
                        content=content,
                        source=source["name"],
                    )
                    if node:
                        async with await get_async_session() as db:
                            repo = IdeaRepo(db)
                            await repo.create(node)
                        new_nodes.append(node)
            except Exception as e:
                logger.error(f"Failed to poll {source['name']}: {e}")

            self._last_poll[source["name"]] = now

        return new_nodes

    async def _fetch_source(self, source: dict) -> Optional[str]:
        """获取外部源内容"""
        import httpx

        if source["type"] == "rss":
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(source["url"])
                    resp.raise_for_status()
                    # 简易 RSS 提取（取 title + description）
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(resp.text)
                    items = []
                    for item in root.iter("item"):
                        title = item.findtext("title", "")
                        desc = item.findtext("description", "")
                        items.append(f"{title}: {desc}")
                    return "\n".join(items[:5])  # 最新 5 条
            except Exception:
                return None

        elif source["type"] == "webhook":
            # Webhook 由外部推送，此处不主动 fetch
            return None

        return None

    @property
    def sources(self) -> List[dict]:
        return list(self._sources)
