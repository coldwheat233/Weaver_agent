"""Q1-L3: 用户反馈训练 — 标记想法为"有用"或"噪音"

通过用户标签积累训练数据, 后续新想法预过滤时参考历史标签
"""

from fastapi import APIRouter
from pydantic import BaseModel
from uuid import UUID
from src.storage.database import get_async_session
from src.storage.idea_repo import IdeaRepo
from src.utils.logging_config import logger

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    idea_id: str
    label: str  # "signal" | "noise"


# 简单内存存储 (单用户桌面应用可以, 多用户需 DB)
_feedback_store: dict[str, list[dict]] = {}


@router.post("")
async def submit_feedback(req: FeedbackRequest):
    """标记想法为 signal 或 noise"""
    import json
    from pathlib import Path
    from src.utils.runtime_config import user_data_root

    if req.label not in ("signal", "noise"):
        return {"ok": False, "error": "label must be 'signal' or 'noise'"}

    # 记录标签
    entry = {"idea_id": req.idea_id, "label": req.label}
    key = "feedback_log"
    if key not in _feedback_store:
        _feedback_store[key] = []
    _feedback_store[key].append(entry)

    # 持久化到用户数据目录
    feedback_path = user_data_root() / "feedback.json"
    existing = []
    if feedback_path.exists():
        try:
            existing = json.loads(feedback_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    existing.append(entry)
    feedback_path.write_text(json.dumps(existing[-200:], ensure_ascii=False, indent=2), encoding="utf-8")

    # 更新对应想法: signal → status=active, noise → status=dormant
    try:
        async with await get_async_session() as db:
            repo = IdeaRepo(db)
            node = await repo.get(UUID(req.idea_id))
            if node:
                from src.core.models import NodeStatus
                if req.label == "noise":
                    await repo.update_status(UUID(req.idea_id), NodeStatus.DORMANT)
                elif req.label == "signal":
                    await repo.update_status(UUID(req.idea_id), NodeStatus.ACTIVE)
    except Exception as e:
        logger.warning(f"Feedback status update failed: {e}")

    logger.info(f"Feedback: {req.idea_id[:8]} → {req.label}")
    return {"ok": True, "total_feedback": len(existing)}


@router.get("/stats")
async def feedback_stats():
    """反馈统计"""
    from pathlib import Path
    import json
    from src.utils.runtime_config import user_data_root

    feedback_path = user_data_root() / "feedback.json"
    logs = []
    if feedback_path.exists():
        try:
            logs = json.loads(feedback_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    signal_count = sum(1 for e in logs if e["label"] == "signal")
    noise_count = sum(1 for e in logs if e["label"] == "noise")
    return {
        "total": len(logs),
        "signal": signal_count,
        "noise": noise_count,
        "signal_ratio": signal_count / max(len(logs), 1),
    }
