"""V3 自治演进路由 —— 外部监听 + 自动提案"""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from src.core.llm_service import LiteLLMService
from src.agents.monitor import MonitorAgent, ExternalSourcePoller
from src.core.trigger import auto_proposal_engine
from src.utils.logging_config import logger

router = APIRouter(prefix="/api/v3", tags=["v3-autonomy"])

llm = LiteLLMService()
monitor = MonitorAgent(llm)
poller = ExternalSourcePoller(monitor)


class AddSourceRequest(BaseModel):
    name: str
    url: str
    source_type: str = "rss"
    poll_interval_minutes: int = 60


class WebhookPayload(BaseModel):
    source_name: str
    content: str
    url: Optional[str] = None


# ── 外部源管理 ──

@router.get("/sources")
async def list_sources():
    return {"sources": poller.sources}


@router.post("/sources")
async def add_source(req: AddSourceRequest):
    poller.add_source(
        name=req.name,
        url=req.url,
        source_type=req.source_type,
        poll_interval_minutes=req.poll_interval_minutes,
    )
    return {"message": f"Source '{req.name}' added", "total_sources": len(poller.sources)}


@router.delete("/sources/{name}")
async def remove_source(name: str):
    poller.remove_source(name)
    return {"message": f"Source '{name}' removed"}


# ── Webhook 推送（外部主动推送内容）──

@router.post("/webhook")
async def receive_webhook(payload: WebhookPayload):
    """接收外部 webhook 推送的内容"""
    node = await monitor.ingest_external(
        content=payload.content,
        source=payload.source_name,
    )

    if node:
        from src.storage.database import get_async_session
        from src.storage.idea_repo import IdeaRepo

        async with await get_async_session() as db:
            repo = IdeaRepo(db)
            await repo.create(node)

        return {
            "ingested": True,
            "idea_id": str(node.id),
            "standardized_content": node.standardized_content,
        }
    else:
        return {"ingested": False, "reason": "not relevant"}


# ── 手动轮询 ──

@router.post("/poll")
async def manual_poll():
    """手动触发一次全量轮询"""
    nodes = await poller.poll_all()
    return {
        "polled": len(poller.sources),
        "new_ideas": len(nodes),
        "idea_ids": [str(n.id) for n in nodes],
    }


# ── 自动提案 ──

@router.post("/scan-and-propose")
async def scan_and_propose():
    """扫描所有概念簇，触发符合条件的自动设计提案"""
    proposals = await auto_proposal_engine.scan_and_propose()
    return {
        "proposals_created": len(proposals),
        "proposals": proposals,
        "pending_total": auto_proposal_engine.get_pending_count(),
    }


@router.get("/proposals")
async def list_proposals(limit: int = 20):
    """查看所有自动提案"""
    return {
        "proposals": await auto_proposal_engine.get_proposals(limit),
        "pending": auto_proposal_engine.get_pending_count(),
    }


# ── 后台轮询任务 ──

@router.post("/start-background-polling")
async def start_background_polling(background_tasks: BackgroundTasks):
    """启动后台轮询（在 FastAPI 的 background_tasks 中间歇运行）"""

    import asyncio

    async def _poll_loop():
        while True:
            try:
                nodes = await poller.poll_all()
                if nodes:
                    # 每次有新想法后扫描一次临界质量
                    await auto_proposal_engine.scan_and_propose()
            except Exception as e:
                logger.error(f"Background poll error: {e}")
            await asyncio.sleep(300)  # 每 5 分钟

    background_tasks.add_task(_poll_loop)
    return {"message": "Background polling started (5min interval)"}


@router.post("/pause")
async def pause_monitoring():
    poller.pause()
    return {"message": "Monitoring paused"}


@router.post("/resume")
async def resume_monitoring():
    poller.resume()
    return {"message": "Monitoring resumed"}
