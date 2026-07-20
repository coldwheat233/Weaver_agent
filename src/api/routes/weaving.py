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
    """直接 Agent 流水线——绕过 LangGraph（稳定优先）"""
    from src.storage.database import get_async_session
    from src.storage.idea_repo import IdeaRepo
    from src.storage.design_repo import DesignRepo
    from uuid import UUID

    # 获取 LLM 服务（runtime_config 驱动）
    from src.core.deepseek_service import OpenAICompatibleService
    llm = OpenAICompatibleService()

    # 加载会话和想法
    async with await get_async_session() as db:
        idea_repo = IdeaRepo(db)
        session = await SessionRepo(db).get(UUID(session_id))
        if not session:
            return {"status": "failed", "error": f"session {session_id} not found"}

        # 通过 session.input_idea_ids 或 list_by_session 获取想法
        if session.input_idea_ids:
            ideas = await idea_repo.get_by_ids(session.input_idea_ids)
        else:
            ideas = await idea_repo.list_by_session(session_id)

    if not ideas:
        return {"status": "failed", "error": "no ideas in session"}

    north_star = session.north_star

    # Step 1: Collector (已在提交时完成)
    # Step 2: Weaver
    from src.agents.weaver import WeaverAgent
    w = WeaverAgent(llm)
    result = await w.weave(ideas, north_star)
    clusters = WeaverAgent.build_clusters_from_result(result, ideas)
    rels = WeaverAgent.build_relationships(result, ideas)
    conflicts = WeaverAgent.build_conflicts(result, ideas)

    # Step 3: Architect
    from src.agents.architect import ArchitectAgent
    a = ArchitectAgent(llm)
    bridges = result.get("cross_domain_bridges", [])
    design = await a.design(
        clusters, rels, bridges,
        [{"type": c.conflict_type.value, "description": c.description} for c in conflicts],
        north_star,
    )

    # Step 4: Critic
    from src.agents.critic import CriticAgent
    cr = CriticAgent(llm)
    fb = await cr.critique(design, ideas)

    # 保存设计
    async with await get_async_session() as db:
        design_repo = DesignRepo(db)
        design.innovation_score = fb.scores.innovation
        design.coherence_score = fb.scores.coherence
        design.feasibility_score = fb.scores.feasibility
        design.critic_approval = fb.approved
        design.critic_feedback = str(fb.blocking_issues) if fb.blocking_issues else None
        await design_repo.create(design)

    logger.info(f"Weave complete: design={design.id} approved={fb.approved}")
    return {"status": "complete", "design_id": str(design.id)}


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
        from src.core.workflow import execute_weave_workflow
        await execute_weave_workflow(session_id)
    except Exception as e:
        logger.error(f"Async weave failed: {e}")
