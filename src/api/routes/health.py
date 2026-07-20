"""健康检查路由"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    from src.utils.config import get_settings
    s = get_settings()
    return {
        "status": "ok",
        "deploy_mode": s.DEPLOY_MODE,
        "db": "ok",
        "version": "0.1.0",
    }
