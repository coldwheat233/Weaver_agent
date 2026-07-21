"""想法提交路由"""

from fastapi import APIRouter, UploadFile, File, Form
from uuid import uuid4
from src.storage.database import get_async_session
from src.storage.idea_repo import IdeaRepo
from src.storage.file_store import FileStore
from src.core.models import SourceType
from src.core.llm_service import LiteLLMService, FakeLLMService
from src.agents.collector import CollectorAgent
from src.utils.logging_config import logger
from src.utils.config import get_settings

router = APIRouter(prefix="/api/ideas", tags=["ideas"])

def _get_llm():
    """从 runtime_config 构建 LLM 服务"""
    try:
        from src.core.deepseek_service import OpenAICompatibleService
        return OpenAICompatibleService()
    except Exception:
        pass
    try:
        return LiteLLMService()
    except Exception:
        pass
    # 降级: Fake
    return FakeLLMService()

llm = _get_llm()
collector = CollectorAgent(llm)
file_store = FileStore()


@router.post("")
async def submit_idea(
    content: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    source_type: str = Form(default="text"),
    session_id: str = Form(default=""),
):
    """提交一条想法"""
    asset_path = None
    actual_source = SourceType.TEXT

    # 处理文件上传
    if file and file.filename:
        data = await file.read()
        if file.content_type and file.content_type.startswith("image"):
            actual_source = SourceType.IMAGE
            asset_path = file_store.save_image(data, f"{uuid4()}_{file.filename}")
        elif file.content_type and file.content_type.startswith("audio"):
            actual_source = SourceType.VOICE
            asset_path = file_store.save_audio(data, f"{uuid4()}_{file.filename}")

    # 处理语音转写（如果 source_type=voice 但内容为空，说明需要转写）
    if actual_source == SourceType.VOICE and not content and asset_path:
        from src.utils.whisper_transcriber import WhisperTranscriber
        transcriber = WhisperTranscriber()
        content = transcriber.transcribe_text_only(asset_path)

    # Collector 标准化
    if not content and not asset_path:
        return {"error": "content 和 file 至少提供一个"}, 400

    actual_content = content or "(图片/语音输入)"
    node = await collector.process(
        content=actual_content,
        source_type=actual_source or SourceType.TEXT,
        asset_path=asset_path,
        session_id=session_id or None,
    )

    # 持久化
    async with await get_async_session() as db:
        repo = IdeaRepo(db)
        await repo.create(node)

        # 如果有 session，关联想法到会话
        if session_id:
            from src.storage.session_repo import SessionRepo
            from uuid import UUID as _UUID
            await SessionRepo(db).add_idea(session_id, node.id)

        # Q7: 更新用户画像 (学习思维模式)
        await _update_user_profile(db, node)

    logger.info(f"Idea submitted: {node.id} session={session_id}")

    return {
        "idea_id": str(node.id),
        "standardized_content": node.standardized_content,
        "intent_tags": [t.value for t in node.intent_tags],
        "status": node.status.value,
    }


async def _update_user_profile(db, node):
    """Q7: 每次提交想法时更新用户画像"""
    import json
    from sqlalchemy import text

    # 读取当前 profile
    result = await db.execute(text("SELECT * FROM user_profile WHERE id = 1"))
    row = result.fetchone()
    if not row: return
    r = dict(row._mapping)

    # 更新 interaction_count
    count = r.get("interaction_count", 0) + 1

    # 更新 frequent_domains (最近 50 条想法的 context_tags 统计)
    domains = json.loads(r.get("frequent_domains", "[]"))
    for tag in node.context_tags:
        if tag not in domains:
            domains.append(tag)
    domains = domains[-30:]  # 保留最近 30 个唯一 domain

    # 更新 idea_transition_matrix (domain → domain 计数的 Markov 链)
    matrix = json.loads(r.get("idea_transition_matrix", "{}"))
    tags = node.context_tags[:3]
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            key = f"{tags[i]}→{tags[j]}"
            matrix[key] = matrix.get(key, 0) + 1

    # 更新 recurring_constraints (检测包含 "必须" / "不能" / "需要" 的想法)
    constraints = json.loads(r.get("recurring_constraints", "[]"))
    content = node.standardized_content or node.raw_content
    for kw in ["必须", "不能", "需要", "要求", "保证", "确保"]:
        if kw in content and content not in constraints:
            constraints.append(content[:120])
    constraints = constraints[-10:]

    await db.execute(text("""
        UPDATE user_profile SET
            frequent_domains = :domains,
            idea_transition_matrix = :matrix,
            recurring_constraints = :constraints,
            interaction_count = :count,
            last_updated = datetime('now')
        WHERE id = 1
    """), {
        "domains": json.dumps(domains, ensure_ascii=False),
        "matrix": json.dumps(matrix, ensure_ascii=False),
        "constraints": json.dumps(constraints, ensure_ascii=False),
        "count": count,
    })
    await db.commit()


@router.get("")
async def list_ideas(limit: int = 50):
    """列出所有想法"""
    from src.storage.database import get_async_session
    from src.storage.idea_repo import IdeaRepo
    async with await get_async_session() as db:
        ideas = await IdeaRepo(db).list_active(limit=limit)
    return [
        {
            "id": str(i.id),
            "source_type": i.source_type.value,
            "raw_content": i.raw_content,
            "standardized_content": i.standardized_content,
            "intent_tags": [t.value for t in i.intent_tags],
            "context_tags": i.context_tags,
            "status": i.status.value,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in ideas
    ]
