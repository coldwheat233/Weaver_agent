"""调试端点 —— 仅开发/Docker 模式启用"""

from fastapi import APIRouter
from src.utils.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/sessions/{session_id}/state-snapshot")
async def get_state_snapshot(session_id: str):
    """获取 LangGraph checkpoint 的当前状态"""
    from langgraph.checkpoint.sqlite import SqliteSaver

    checkpoint_path = str(settings.checkpoint_db_path)
    try:
        checkpointer = SqliteSaver.from_conn_string(checkpoint_path)
        config = {"configurable": {"thread_id": session_id}}
        state = checkpointer.get(config)
        if state:
            return {"session_id": session_id, "state": state}
        return {"session_id": session_id, "state": None, "message": "no checkpoint found"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/graph/{session_id}")
async def get_idea_graph(session_id: str):
    """导出当前会话的想法图谱 JSON（D3.js 可用）"""
    from src.storage.database import get_async_session
    from src.storage.idea_repo import IdeaRepo
    from src.core.graph_ops import GraphOps

    async with await get_async_session() as db:
        repo = IdeaRepo(db)
        ideas = await repo.list_by_session(session_id)

    nodes = [{"id": str(i.id)[:8], "label": (i.standardized_content or i.raw_content)[:60],
              "type": i.source_type.value, "tags": [t.value for t in i.intent_tags],
              "domains": i.context_tags} for i in ideas]

    return {"session_id": session_id, "nodes": nodes, "node_count": len(nodes)}


@router.get("/llm-calls")
async def get_llm_calls():
    """查看 LLM 调用统计（需 LLMTracer 集成）"""
    return {
        "message": "LLMTracer not yet integrated. See src/utils/tracing.py for span utilities.",
        "hint": "Wrap agent calls with: from src.utils.tracing import span; async with span('agent','task'): ...",
    }


@router.get("/prompts/{agent_name}")
async def preview_prompt(agent_name: str, session_id: str = ""):
    """预览某 Agent 的完整系统 prompt"""
    from src.agents.prompts import get_system_prompt
    try:
        system = get_system_prompt(agent_name)
        return {"agent": agent_name, "system_prompt": system,
                "length_chars": len(system), "estimated_tokens": len(system) // 4}
    except Exception as e:
        return {"error": str(e)}


@router.get("/config")
async def get_config():
    """查看当前配置（不含密钥）"""
    return {
        "deploy_mode": settings.DEPLOY_MODE,
        "api_port": settings.api_port,
        "data_dir": str(settings.data_dir),
        "weaver_model": settings.WEAVER_MODEL,
        "light_model": settings.LIGHT_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "max_iterations": settings.WEAVER_MAX_ITERATIONS,
        "use_async_weave": settings.use_async_weave,
    }
