"""状态序列化 —— WeaverSession 的持久化与恢复"""

from typing import Optional
from src.core.models import WeaverSession
from src.storage.database import get_async_session
from src.storage.session_repo import SessionRepo
from src.utils.logging_config import logger


async def save_session(session: WeaverSession):
    """保存或更新会话状态"""
    async with await get_async_session() as db:
        repo = SessionRepo(db)
        existing = await repo.get(session.id)
        if existing:
            await repo.update_status(str(session.id), session.status.value)
        else:
            await repo.create(session)


async def load_session(session_id: str) -> Optional[WeaverSession]:
    """加载会话状态"""
    async with await get_async_session() as db:
        repo = SessionRepo(db)
        from uuid import UUID
        return await repo.get(UUID(session_id))


async def checkpoint_workflow_state(session_id: str, state: dict):
    """保存 LangGraph checkpoint（由 LangGraph SQLite checkpointer 自动处理，
    此处作为补充，持久化高级状态）"""
    from src.storage.database import AsyncSessionLocal
    from sqlalchemy import text

    import json

    async with AsyncSessionLocal() as db:
        # 保存 phases 到 weaver_sessions 的备注（可扩展）
        serializable = {
            "iteration": state.get("iteration", 0),
            "status": state.get("status", ""),
        }
        await db.execute(
            text("UPDATE weaver_sessions SET errors = :err WHERE id = :id"),
            {"id": session_id, "err": json.dumps(state.get("errors", []))},
        )
        await db.commit()

    logger.bind(component="state_manager").debug(f"Checkpoint saved for session {session_id}")
