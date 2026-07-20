"""编织用例 Service 层 —— 第 17 章解耦方案

API 路由只依赖此抽象，隔离 LangGraph 实现细节。
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from src.core.models import WeaverSession, DesignDocument
from src.utils.logging_config import logger


class WeavingService(ABC):
    """编织用例的抽象接口"""

    @abstractmethod
    async def start_weave(self, session_id: str,
                          divergence_degree: int = 2) -> dict:
        """触发编织，返回 {status, design_id, ...}"""
        ...

    @abstractmethod
    async def get_progress(self, session_id: str) -> dict:
        """查询编织进度"""
        ...


class LangGraphWeavingService(WeavingService):
    """基于 LangGraph 的实现"""

    async def start_weave(self, session_id: str,
                          divergence_degree: int = 2) -> dict:
        from src.storage.database import get_async_session
        from src.storage.session_repo import SessionRepo
        from src.core.workflow import execute_weave_workflow

        # 验证会话
        async with await get_async_session() as db:
            repo = SessionRepo(db)
            session = await repo.get(UUID(session_id))
            if not session:
                raise ValueError(f"Session {session_id} not found")
            await repo.update_status(session_id, "weaving")

        try:
            result = await execute_weave_workflow(session_id)
            logger.info(f"Weave complete: session={session_id}, {result.get('status')}")
            return result
        except Exception as e:
            logger.error(f"Weave failed: {e}")
            async with await get_async_session() as db:
                repo = SessionRepo(db)
                await repo.mark_failed(session_id, str(e))
            raise

    async def get_progress(self, session_id: str) -> dict:
        from src.storage.database import get_async_session
        from src.storage.session_repo import SessionRepo

        async with await get_async_session() as db:
            repo = SessionRepo(db)
            session = await repo.get(UUID(session_id))

        if not session:
            return {"error": "not found"}

        progress_map = {
            "collecting": 0.1, "weaving": 0.4, "architecting": 0.7,
            "critiquing": 0.9, "complete": 1.0, "failed": 1.0,
        }
        return {
            "session_id": session_id,
            "status": session.status.value if hasattr(session.status, 'value') else session.status,
            "progress": progress_map.get(
                session.status.value if hasattr(session.status, 'value') else session.status, 0.0,
            ),
            "design_id": str(session.output_design_id) if session.output_design_id else None,
        }


# 全局单例（可被 DI 替换）
weaving_service: WeavingService = LangGraphWeavingService()
