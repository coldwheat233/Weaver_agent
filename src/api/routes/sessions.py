"""会话管理路由"""

from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4
from src.storage.database import get_async_session
from src.storage.session_repo import SessionRepo
from src.storage.idea_repo import IdeaRepo
from src.core.models import WeaverSession

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    north_star: str
    divergence_degree: int = 2


@router.post("")
async def create_session(req: CreateSessionRequest):
    """创建编织会话"""
    session = WeaverSession(
        id=uuid4(),
        north_star=req.north_star,
        divergence_degree=req.divergence_degree,
    )
    async with await get_async_session() as db:
        repo = SessionRepo(db)
        await repo.create(session)

    return {
        "session_id": str(session.id),
        "north_star": session.north_star,
        "status": session.status.value,
    }


@router.get("/{session_id}")
async def get_session(session_id: str):
    """获取会话状态"""
    from uuid import UUID
    async with await get_async_session() as db:
        repo = SessionRepo(db)
        session = await repo.get(UUID(session_id))
        if not session:
            return {"error": "not found"}, 404

    return {
        "session_id": str(session.id),
        "north_star": session.north_star,
        "status": session.status.value,
        "input_idea_ids": [str(i) for i in session.input_idea_ids],
        "output_design_id": str(session.output_design_id) if session.output_design_id else None,
        "errors": session.errors,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


@router.get("/{session_id}/ideas")
async def get_session_ideas(session_id: str):
    """获取会话中的所有想法"""
    async with await get_async_session() as db:
        idea_repo = IdeaRepo(db)
        ideas = await idea_repo.list_by_session(session_id)

    return {
        "session_id": session_id,
        "ideas": [
            {
                "id": str(i.id),
                "standardized_content": i.standardized_content,
                "source_type": i.source_type.value,
                "intent_tags": [t.value for t in i.intent_tags],
                "status": i.status.value,
            }
            for i in ideas
        ],
    }
