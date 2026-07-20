# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Mirror Configuration (ALWAYS do this first)

When installing ANY package manager tooling (pip, npm, cargo, rustup), **immediately check if a Chinese mirror is needed** and configure it before proceeding:

```bash
# pip (Python)
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# npm (Node.js)
npm config set registry https://registry.npmmirror.com

# Cargo (Rust) — use sparse protocol for speed
mkdir -p ~/.cargo
cat > ~/.cargo/config.toml << 'EOF'
[source.crates-io]
replace-with = "ustc-sparse"
[source.ustc-sparse]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"
[net]
git-fetch-with-cli = true
EOF

# Rustup (Rust toolchain)
export RUSTUP_DIST_SERVER=https://mirrors.ustc.edu.cn/rust-static
export RUSTUP_UPDATE_ROOT=https://mirrors.ustc.edu.cn/rust-static/rustup
```

**Never start a long download without mirrors configured.** If download speed seems slow, stop and check mirrors first.

## Commands

```bash
# Python backend tests (no external deps needed)
python -m pytest tests/ -q

# Full pipeline test (requires OPENAI_API_KEY in env)
python run.py test

# Start API server
python run.py server       # → http://localhost:8765/docs

# Desktop mode (Tauri 2 + React, requires Rust + Node.js)
cd desktop && npm install && cd ..
python run.py tauri         # First build takes ~10min (Rust compilation)

# Tauri dev directly (after npm install)
cd desktop && .\node_modules\.bin\tauri.cmd dev
```

## Architecture

**Dual-runtime**: Python backend (AI agents + API) + Tauri desktop shell (Rust + React).

```
┌─ Tauri 2 (Rust) ──────────────────────┐
│  React 18 UI (WebView2 rendering)      │
│  · CaptureOverlay.tsx (Ctrl+Alt+[)    │
│  · Dashboard.tsx     (Ctrl+Alt+])    │
│  System tray + global hotkeys          │
│         │ HTTP localhost:8765          │
├────────────────────────────────────────┤
│  Python FastAPI backend                │
│  · Collector → Weaver → Architect → Critic
│  · DeepSeekService (httpx, no litellm needed)
│  · SQLite + ChromaDB storage           │
└────────────────────────────────────────┘
```

### Python Backend (`src/`)

- `src/main.py` — Entry point. Modes: `desktop` (Tkinter fallback), `server`, `docker`, `fc`.
- `src/api/server.py` — FastAPI app. All routes at `/api/*`, static files at `/static/*`, dashboard at `/dashboard`.
- `src/agents/` — Four-agent pipeline: `collector.py`, `weaver/` (4 sub-components), `architect.py`, `critic.py`. V2: `inquisitor.py`. V3: `monitor.py`.
- `src/core/` — `models.py` (14 Pydantic entities), `workflow.py` (LangGraph + Node Registry), `deepseek_service.py` (httpx direct, no litellm), `retrieval.py` (HybridRetriever + TruncationPolicy), `trigger.py` (V3 auto-proposal).
- `src/storage/` — SQLite via SQLAlchemy + aiosqlite. ChromaDB for vectors. Repo pattern: one file per entity.
- `src/ui/overlay_window.py` — Tkinter fallback overlay (DPI-aware). **Being replaced by Tauri.**
- **API key**: set `OPENAI_API_KEY` in `.env`. Default model is `deepseek-chat` via `https://api.deepseek.com`.

### Tauri Desktop Shell (`desktop/`)

- `desktop/src-tauri/` — Rust backend: `main.rs` (spawns Python, tray icon, global shortcuts), `tauri.conf.json` (frameless transparent windows).
- `desktop/src/` — React frontend: `CaptureOverlay.tsx`, `Dashboard.tsx`, `globals.css` (DESIGN.md tokens).
- Two windows: `input` (560×520, always-on-top) and `dashboard` (620×580, resizable). Both frameless + transparent for CSS border-radius.
- Tray: left-click toggles dashboard, right-click shows menu (Input / Dashboard / Quit).
- **First `tauri dev` build is slow** (~10min Rust compilation). Subsequent builds use cached artifacts.

### Deployment

- `Dockerfile` + `docker-compose.yml` — Single container, port 8765.
- `s.yaml` — Alibaba Cloud FC serverless (two functions: API + async worker).
- `run.py` — Unified launcher: `python run.py [server|desktop|tauri|test]`.
- **打包分发**: `scripts/build_backend.bat` (PyInstaller sidecar) → copy to `desktop/src-tauri/binaries/` → `npm run tauri build`. Tag `v*` 触发 `.github/workflows/release.yml` CI 打包。

### Model Configurator (运行时配置)

模型配置三层优先级: `~/.weaver/config.json` > `.env` > 内置默认(DeepSeek)。

- `src/utils/runtime_config.py` — config.json 读写, `RuntimeConfig.masked()` 脱敏
- `src/api/routes/config.py` — `GET/PUT /api/config`, `POST /api/config/test`
- `src/core/deepseek_service.py` — `OpenAICompatibleService` 泛化服务 (DeepSeek/OpenAI/Ollama/custom 全走 OpenAI 协议), `DeepSeekService` 为其别名
- 前端: `desktop/src/components/Settings.tsx`, Dashboard ⚙ 入口 + 未配置横幅
- 数据目录: desktop 模式统一在 `~/.weaver/data`（打包后程序目录不可写）

## Key Design Decisions

1. **No litellm dependency at runtime** — `src/core/deepseek_service.py` calls DeepSeek API directly via httpx. The LLMService ABC allows swapping implementations.
2. **Node Registry pattern** — Workflow nodes self-register via `@register_node`. `workflow.py` only wires the graph, doesn't import agents.
3. **Agent pipeline bypasses LangGraph** — API weave route (`weaving.py:_run_weave_pipeline`) calls agents directly for reliability. LangGraph workflow exists but is unused in production path.
4. **Session-linked ideas** — Ideas must be submitted with `session_id` for weaving to find them. The API auto-creates a session on first submit.
5. **DEPLOY_MODE env** — `desktop|docker|fc` controls storage paths, port, and async mode.
