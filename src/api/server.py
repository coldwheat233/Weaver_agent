"""FastAPI 应用定义"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.utils.config import get_settings
from src.utils.logging_config import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    from src.storage.database import init_db
    await init_db()
    logger.info(f"WEAVE server starting on port {settings.api_port} (mode={settings.DEPLOY_MODE})")
    yield
    logger.info("WEAVE server shutting down")


app = FastAPI(
    title="Idea Weaver",
    description="碎碎念到结构化设计文档的 AI 助手",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.responses import HTMLResponse

# ── 根路由 ──
@app.get("/")
async def root():
    return {"app": "Idea Weaver", "version": "0.1.0", "docs": "/docs", "health": "/api/health"}


# ── Dashboard ──
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    dp = _Path(__file__).parent.parent / "ui" / "static" / "dashboard.html"
    if dp.exists():
        return dp.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


# ── 捕获页（浏览器降级）──
from pathlib import Path as _Path


@app.get("/ui/capture", response_class=HTMLResponse)
async def capture_page():
    html_path = _Path(__file__).parent.parent / "ui" / "static" / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Capture page not found</h1>", status_code=404)


# ── 静态文件路由 (CSS / JS) ──
import os as _os

def _get_static_dir():
    for candidate in [
        _Path(_os.path.abspath(__file__)).parent.parent / "ui" / "static",
        _Path.cwd() / "src" / "ui" / "static",
    ]:
        d = candidate.resolve()
        if d.exists():
            return d
    return None

_STATIC = _get_static_dir()

def _read_static(filename: str) -> str:
    if _STATIC:
        p = _STATIC / filename
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""

@app.get("/static/styles.css", response_class=HTMLResponse)
async def css_styles():
    return HTMLResponse(_read_static("styles.css"), media_type="text/css")

@app.get("/static/app.js", response_class=HTMLResponse)
async def js_app():
    return HTMLResponse(_read_static("app.js"), media_type="application/javascript")

@app.get("/static/results.css", response_class=HTMLResponse)
async def css_results():
    return HTMLResponse(_read_static("results.css"), media_type="text/css")

@app.get("/static/results.js", response_class=HTMLResponse)
async def js_results():
    return HTMLResponse(_read_static("results.js"), media_type="application/javascript")

# ── 路由注册 ──
from src.api.routes import ideas, sessions, weaving, designs, health, assets, v2_dialogue, v3_autonomy, debug, config, feedback  # noqa: E402

app.include_router(health.router)
app.include_router(ideas.router)
app.include_router(sessions.router)
app.include_router(weaving.router)
app.include_router(designs.router)
app.include_router(assets.router)
app.include_router(v2_dialogue.router)
app.include_router(v3_autonomy.router)
app.include_router(debug.router)
app.include_router(config.router)
app.include_router(feedback.router)
