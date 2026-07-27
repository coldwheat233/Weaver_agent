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

async def run_weave_pipeline(session_id: str) -> dict:
    """执行一次完整的编织流水线 — Collector → Weaver → Architect → Critic.

    带混合检索增强 + Critic 反馈迭代。
    返回 {"design_id": str, "status": str}
    """
    from src.storage.database import get_async_session
    from src.storage.idea_repo import IdeaRepo
    from src.storage.design_repo import DesignRepo
    from src.storage.session_repo import SessionRepo
    from uuid import UUID

    from src.core.deepseek_service import OpenAICompatibleService
    llm = OpenAICompatibleService()

    # 加载会话和想法
    async with await get_async_session() as db:
        idea_repo = IdeaRepo(db)
        session = await SessionRepo(db).get(UUID(session_id))
        if not session:
            return {"status": "failed", "error": f"session {session_id} not found"}

        if session.input_idea_ids:
            ideas = await idea_repo.get_by_ids(session.input_idea_ids)
        else:
            ideas = await idea_repo.list_by_session(session_id)

    if not ideas:
        return {"status": "failed", "error": "no ideas in session"}

    north_star = session.north_star

    # ── 混合检索增强 ──
    try:
        from src.storage.vector_store import VectorStore
        from src.core.embeddings import EmbeddingService
        from src.core.retrieval import HybridRetriever

        emb_svc = EmbeddingService()
        vec_store = VectorStore()

        async with await get_async_session() as db2:
            retriever = HybridRetriever(vec_store, IdeaRepo(db2), emb_svc)
            historical = await retriever.retrieve_for_weaving(
                north_star=north_star,
                new_node_ids=[idea.id for idea in ideas],
                divergence_degree=getattr(session, 'divergence_degree', None) or 2,
                max_nodes=20,
            )

        current_ids = {idea.id for idea in ideas}
        new_count = 0
        for h in historical:
            if h.id not in current_ids:
                ideas.append(h)
                current_ids.add(h.id)
                new_count += 1

        if new_count > 0:
            logger.info(
                f"Hybrid retrieval enriched weave: {new_count} historical ideas "
                f"(total {len(ideas)} nodes)"
            )
    except Exception as e:
        logger.warning(f"Hybrid retrieval skipped (embeddings may not be configured): {e}")

    # ── Agent 流水线 (带 Critic 反馈迭代) ──
    max_iter = getattr(session, 'max_iterations', None) or settings.WEAVER_MAX_ITERATIONS
    feedback = None

    for iteration in range(1, max_iter + 1):
        # Weaver
        from src.agents.weaver import WeaverAgent
        w = WeaverAgent(llm)
        result = await w.weave(ideas, north_star, feedback=feedback)
        clusters = WeaverAgent.build_clusters_from_result(result, ideas)
        rels = WeaverAgent.build_relationships(result, ideas)
        conflicts = WeaverAgent.build_conflicts(result, ideas)

        # Architect
        from src.agents.architect import ArchitectAgent
        a = ArchitectAgent(llm)
        bridges = result.get("cross_domain_bridges", [])
        design = await a.design(
            clusters, rels, bridges,
            [{"type": c.conflict_type.value, "description": c.description} for c in conflicts],
            north_star,
        )

        # Critic (with static Pass1 pre-check)
        from src.agents.critic import CriticAgent
        cr = CriticAgent(llm)
        fb = await cr.critique(design, ideas)

        if fb.approved:
            logger.info(f"Weave passed critic on iteration {iteration}")
            break

        if iteration < max_iter:
            logger.info(
                f"Weave iteration {iteration} rejected "
                f"(coherence={fb.scores.coherence:.2f} feasibility={fb.scores.feasibility:.2f}), "
                f"re-weaving..."
            )
            feedback = {
                "blocking_issues": fb.blocking_issues,
                "suggestions": fb.suggestions,
                "feedback": fb.feedback,
            }
        else:
            logger.warning(f"Max iterations ({max_iter}) reached, accepting best result")

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


# ── deprecated: 旧 LangGraph 路径，未实现，请使用 run_weave_pipeline ──
async def execute_weave_workflow(session_id: str) -> dict:
    """[已废弃] 请使用 run_weave_pipeline()"""
    logger.warning("execute_weave_workflow is deprecated, redirecting to run_weave_pipeline")
    return await run_weave_pipeline(session_id)


# ═══════════════════════════════════════════
# 检查器（供 should_iterate 使用）
# ═══════════════════════════════════════════

"""LangGraph checkpoint 路径在编译时读取一次；
后续 SQLite checkpointer 在 execute_weave_workflow 内每次创建新实例。"""
