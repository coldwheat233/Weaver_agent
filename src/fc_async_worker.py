"""FC 异步编织 Worker —— 处理超过 60s 的编织任务

FC HTTP 触发器有 600s 超时上限，但 LLM 编织可能超出。
异步 Worker 由 EventBridge 触发，超时可达 24 小时。
"""

import json
import sys
import os
import asyncio

sys.path.insert(0, '/code')
sys.path.insert(0, '/opt/python/lib/python3.11/site-packages')

from src.utils.logging_config import setup_logging
from src.utils.config import get_settings

logger = setup_logging(get_settings().LOG_LEVEL)


async def handle_weave_event(event: dict):
    session_id = event.get("session_id")
    if not session_id:
        logger.error("Missing session_id in event")
        return {"status": "error", "error": "missing session_id"}

    logger.info(f"Async weave starting for session {session_id}")

    from src.core.workflow import execute_weave_workflow
    from src.storage.database import get_async_session
    from src.storage.session_repo import SessionRepo
    from uuid import UUID

    try:
        result = await execute_weave_workflow(session_id)
        logger.info(f"Async weave complete: {result}")
        return result
    except Exception as e:
        logger.error(f"Async weave failed: {e}")
        async with await get_async_session() as db:
            repo = SessionRepo(db)
            await repo.mark_failed(session_id, str(e))
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    event_data = json.loads(sys.stdin.read())
    result = asyncio.run(handle_weave_event(event_data))
    print(json.dumps(result))
