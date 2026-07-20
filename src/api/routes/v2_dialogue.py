"""V2 多轮对话路由 —— 交互式编织"""

from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4
from src.storage.database import get_async_session
from src.storage.session_repo import SessionRepo
from src.storage.idea_repo import IdeaRepo
from src.storage.cluster_repo import ClusterRepo
from src.core.llm_service import LiteLLMService
from src.agents.inquisitor import InquisitorAgent, DialogueManager
from src.utils.logging_config import logger

router = APIRouter(prefix="/api/v2", tags=["v2-dialogue"])

llm = LiteLLMService()
inquisitor = InquisitorAgent(llm)

# 内存中的对话管理器（单用户桌面应用可以，多用户需改为 DB 存储）
_dialogues: dict[str, DialogueManager] = {}


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class DesignDiffRequest(BaseModel):
    design_id_a: str
    design_id_b: str


@router.post("/ask")
async def ask_questions(session_id: str):
    """分析当前会话的想法缺口，生成追问"""
    from uuid import UUID

    async with await get_async_session() as db:
        session_repo = SessionRepo(db)
        session = await session_repo.get(UUID(session_id))
        if not session:
            return {"error": "session not found"}, 404

        idea_repo = IdeaRepo(db)
        # 优先用 session.input_idea_ids，否则按 session_id 过滤
        if session.input_idea_ids:
            ideas = await idea_repo.get_by_ids(session.input_idea_ids)
        else:
            ideas = await idea_repo.list_by_session(session_id)

        cluster_repo = ClusterRepo(db)
        clusters = await cluster_repo.list_active()

    if not ideas:
        return {"questions": [], "message": "还没有收集到任何想法"}

    # Inquisitor 分析缺口
    result = await inquisitor.interrogate(
        clusters=clusters,
        nodes=ideas,
        north_star=session.north_star,
    )

    # 存储对话
    if session_id not in _dialogues:
        _dialogues[session_id] = DialogueManager()

    for q in result.get("questions", []):
        _dialogues[session_id].add_agent_question(q["question"])

    return {
        "session_id": session_id,
        "questions": result.get("questions", []),
        "completeness_estimate": result.get("completeness_estimate", 0),
        "ready_to_architect": result.get("ready_to_architect", False),
        "dialogue_turns": _dialogues[session_id].turn_count,
    }


@router.post("/answer")
async def submit_answer(req: AnswerRequest):
    """用户回答 Agent 的追问"""

    # 将答案作为新想法存储
    from uuid import UUID
    from src.agents.collector import CollectorAgent
    from src.core.models import SourceType

    # 标准化用户的回答
    node = await CollectorAgent(llm).process(
        content=req.answer,
        source_type=SourceType.TEXT,
        session_id=req.session_id,
    )

    async with await get_async_session() as db:
        repo = IdeaRepo(db)
        await repo.create(node)

    # 更新对话
    if req.session_id in _dialogues:
        _dialogues[req.session_id].add_user_answer(req.answer)

    return {
        "idea_id": str(node.id),
        "standardized_content": node.standardized_content,
        "dialogue_turns": _dialogues.get(req.session_id, DialogueManager()).turn_count,
    }


@router.post("/design-diff")
async def design_diff(req: DesignDiffRequest):
    """对比两个版本的设计文档"""
    from uuid import UUID
    import difflib

    async with await get_async_session() as db:
        from src.storage.design_repo import DesignRepo
        repo = DesignRepo(db)
        doc_a = await repo.get(UUID(req.design_id_a))
        doc_b = await repo.get(UUID(req.design_id_b))

    if not doc_a or not doc_b:
        return {"error": "design not found"}, 404

    # 生成 diff
    diff = difflib.unified_diff(
        doc_a.content_markdown.splitlines(keepends=True),
        doc_b.content_markdown.splitlines(keepends=True),
        fromfile=f"v{doc_a.version}: {doc_a.title}",
        tofile=f"v{doc_b.version}: {doc_b.title}",
    )

    return {
        "version_a": doc_a.version,
        "version_b": doc_b.version,
        "title_a": doc_a.title,
        "title_b": doc_b.title,
        "diff": "".join(diff),
        "score_changes": {
            "innovation": doc_b.innovation_score - doc_a.innovation_score,
            "coherence": doc_b.coherence_score - doc_a.coherence_score,
            "feasibility": doc_b.feasibility_score - doc_a.feasibility_score,
        },
    }


@router.post("/rollback")
async def rollback_design(design_id: str, target_version: int = 1):
    """回滚到指定版本"""
    from uuid import UUID

    async with await get_async_session() as db:
        from src.storage.design_repo import DesignRepo
        repo = DesignRepo(db)

        # 追溯版本链
        current = await repo.get(UUID(design_id))
        if not current:
            return {"error": "design not found"}, 404

        target = current
        while target and target.version > target_version:
            if target.parent_design_id:
                target = await repo.get(target.parent_design_id)
            else:
                break

        if not target:
            return {"error": f"version {target_version} not found in lineage"}, 404

        return {
            "rolled_back_to": target.version,
            "design_id": str(target.id),
            "title": target.title,
            "created_at": target.created_at.isoformat() if target.created_at else None,
        }
