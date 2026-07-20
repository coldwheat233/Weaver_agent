"""WebSocket 进度推送 —— 桌面/Docker 模式"""

from fastapi import WebSocket
from typing import Dict
from src.utils.logging_config import logger


class WebSocketManager:
    """管理活跃的 WebSocket 连接"""

    def __init__(self):
        self._connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        if session_id not in self._connections:
            self._connections[session_id] = []
        self._connections[session_id].append(ws)
        logger.debug(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str, ws: WebSocket):
        if session_id in self._connections:
            self._connections[session_id].remove(ws)
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, data: dict):
        """向某会话的所有 WebSocket 客户端推送"""
        if session_id in self._connections:
            for ws in self._connections[session_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    self.disconnect(session_id, ws)

    async def send_progress(self, session_id: str, phase: str, message: str,
                            progress: float, detail: dict | None = None):
        """推送进度消息"""
        await self.broadcast(session_id, {
            "phase": phase,
            "message": message,
            "progress": progress,
            "detail": detail,
        })


ws_manager = WebSocketManager()
