"""LangGraph 编织工作流 —— 系统的中枢神经

第 17 章解耦方案：Node Registry 模式。
Agent 自注册节点，workflow 只负责编排图结构。
"""

from typing import Dict, Callable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from src.core.models import WeaverState
from src.utils.config import get_settings
from src.utils.logging_config import logger

settings = get_settings()

# ═══════════════════════════════════════════
# Node Registry（第 17 章解耦）
# ═══════════════════════════════════════════

_NODE_REGISTRY: Dict[str, Callable] = {}


def register_node(name: str):
    """装饰器：Agent 自注册工作流节点"""
    def decorator(func):
        _NODE_REGISTRY[name] = func
        return func
    return decorator


def get_node(name: str) -> Callable:
    if name not in _NODE_REGISTRY:
        raise KeyError(f"Node '{name}' not registered. Available: {list(_NODE_REGISTRY.keys())}")
    return _NODE_REGISTRY[name]


# ═══════════════════════════════════════════
# 工作流构建
# ═══════════════════════════════════════════

def build_weaving_workflow() -> StateGraph:
    """构建 LangGraph 编织工作流。

    图结构：
      collect_and_prepare → semantic_cluster → build_relationships
        → generate_design → critique → [iterate|finalize|error]
    """
    workflow = StateGraph(WeaverState)

    # 添加节点（从 registry 获取）
    for node_name in [
        "collect_and_prepare",
        "semantic_cluster",
        "build_relationships",
        "generate_design",
        "critique",
        "finalize",
    ]:
        if node_name in _NODE_REGISTRY:
            workflow.add_node(node_name, _NODE_REGISTRY[node_name])

    # 主流程边
    workflow.add_edge("collect_and_prepare", "semantic_cluster")
    workflow.add_edge("semantic_cluster", "build_relationships")
    workflow.add_edge("build_relationships", "generate_design")
    workflow.add_edge("generate_design", "critique")

    # 条件边：迭代或结束
    workflow.add_conditional_edges(
        "critique",
        _should_iterate,
        {
            "iterate": "build_relationships",
            "finalize": "finalize",
            "error": END,
        }
    )

    workflow.add_edge("finalize", END)
    workflow.set_entry_point("collect_and_prepare")
    return workflow


def _should_iterate(state: WeaverState) -> str:
    """Critic 后判定：继续迭代 / 通过 / 报错"""
    if state.get("errors"):
        return "error"

    phases = state.get("phases", {})
    critique_phase = phases.get("critique", {})
    scores = critique_phase.get("critic_scores", {}) if isinstance(critique_phase, dict) else {}

    coherence = scores.get("coherence", 0)
    feasibility = scores.get("feasibility", 0)
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", settings.WEAVER_MAX_ITERATIONS)

    # 通过条件
    if coherence >= 0.6 and feasibility >= 0.5:
        return "finalize"
    if iteration >= max_iter:
        logger.warning(f"Max iterations ({max_iter}) reached, forcing finalize")
        return "finalize"
    return "iterate"


# ═══════════════════════════════════════════
# 工作流执行
# ═══════════════════════════════════════════

async def execute_weave_workflow(session_id: str) -> dict:
    """执行一次完整的编织工作流。

    返回 {"design_id": str, "status": str}
    """
    from src.storage.database import get_async_session
    from src.storage.session_repo import SessionRepo
    from uuid import UUID

    async with await get_async_session() as db:
        repo = SessionRepo(db)
        session = await repo.get(UUID(session_id))
        if not session:
            raise ValueError(f"Session {session_id} not found")

    # 初始状态
    initial_state: WeaverState = {
        "session_id": session_id,
        "north_star": session.north_star,
        "iteration": 1,
        "max_iterations": settings.WEAVER_MAX_ITERATIONS,
        "status": "weaving",
        "errors": [],
        "phases": {},
    }

    # 编译带 checkpoint 的工作流
    checkpoint_path = str(settings.checkpoint_db_path)
    checkpointer = SqliteSaver.from_conn_string(checkpoint_path)
    workflow = build_weaving_workflow()
    app = workflow.compile(checkpointer=checkpointer)

    # 执行
    config = {"configurable": {"thread_id": session_id}}
    final_state = await app.ainvoke(initial_state, config)

    # 更新会话状态
    async with await get_async_session() as db:
        repo = SessionRepo(db)
        if final_state.get("errors"):
            await repo.mark_failed(session_id, "; ".join(final_state["errors"]))
            return {"status": "failed", "errors": final_state["errors"]}

        # 从 phases 中提取 design_id
        phases = final_state.get("phases", {})
        design_phase = phases.get("design", {})
        design_id = design_phase.get("design_id", "") if isinstance(design_phase, dict) else ""

        await repo.mark_complete(session_id, str(design_id))
        logger.info(f"Workflow complete for session {session_id}, design={design_id}")
        return {"status": "complete", "design_id": str(design_id)}


# ═══════════════════════════════════════════
# 检查器（供 should_iterate 使用）
# ═══════════════════════════════════════════

"""LangGraph checkpoint 路径在编译时读取一次；
后续 SQLite checkpointer 在 execute_weave_workflow 内每次创建新实例。"""
