"""编织触发路由"""

from fastapi import APIRouter
from pydantic import BaseModel
from src.storage.database import get_async_session
from src.storage.session_repo import SessionRepo
from src.utils.config import get_settings
from src.utils.logging_config import logger

router = APIRouter(prefix="/api/sessions", tags=["weaving"])

settings = get_settings()


class WeaveRequest(BaseModel):
    divergence_degree: int = 2


@router.post("/{session_id}/weave")
async def trigger_weave(session_id: str, req: WeaveRequest = WeaveRequest()):
    """触发编织。

    桌面/Docker 模式：同步执行（阻塞请求直到完成）
    FC 模式：异步触发（秒返 202，EventBridge Worker 执行）
    """
    # 验证会话存在
    from uuid import UUID
    async with await get_async_session() as db:
        repo = SessionRepo(db)
        session = await repo.get(UUID(session_id))
        if not session:
            return {"error": "session not found"}, 404

    # 更新状态（新 session）
    async with await get_async_session() as db:
        await SessionRepo(db).update_status(session_id, "weaving")

    if settings.use_async_weave:
        _trigger_async_weave(session_id)
        return {
            "session_id": session_id,
            "status": "weaving",
            "mode": "async",
            "message": "编织已触发",
        }
    else:
        try:
            result = await _run_weave_pipeline(session_id)
            return {
                "session_id": session_id,
                "status": result.get("status", "unknown"),
                "design_id": result.get("design_id"),
            }
        except Exception as e:
            import traceback
            logger.error(f"Weave failed: {e}\n{traceback.format_exc()}")
            async with await get_async_session() as db:
                await SessionRepo(db).mark_failed(session_id, str(e))
            return {"session_id": session_id, "status": "failed", "error": str(e)}, 500


@router.get("/{session_id}/progress")
async def poll_progress(session_id: str):
    """轮询编织进度（FC 降级）"""
    from uuid import UUID
    async with await get_async_session() as db:
        repo = SessionRepo(db)
        session = await repo.get(UUID(session_id))

    if not session:
        return {"error": "not found"}, 404

    progress_map = {
        "collecting": 0.1,
        "weaving": 0.4,
        "architecting": 0.7,
        "critiquing": 0.9,
        "complete": 1.0,
        "failed": 1.0,
    }

    return {
        "session_id": session_id,
        "status": session.status.value,
        "progress": progress_map.get(session.status.value, 0.0),
        "design_id": str(session.output_design_id) if session.output_design_id else None,
    }


async def _run_weave_pipeline(session_id: str) -> dict:
    """调用统一编织流水线"""
    from src.core.workflow import run_weave_pipeline
    return await run_weave_pipeline(session_id)


async def _get_session_north_star(session_id: str):
    from uuid import UUID
    from src.storage.database import get_async_session
    from src.storage.session_repo import SessionRepo
    async with await get_async_session() as db:
        return await SessionRepo(db).get(UUID(session_id))


def _trigger_async_weave(session_id: str):
    """FC 异步编织触发（通过 EventBridge）"""
    # 简化版本：在新的事件循环中创建后台任务
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_async_weave(session_id))
        else:
            asyncio.run(_async_weave(session_id))
    except RuntimeError:
        asyncio.run(_async_weave(session_id))


async def _async_weave(session_id: str):
    """后台异步编织"""
    try:
        from src.core.workflow import run_weave_pipeline
        await run_weave_pipeline(session_id)
    except Exception as e:
        logger.error(f"Async weave failed: {e}")
