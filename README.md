# Idea Weaver

> 碎碎念到结构化设计文档的 AI 助手
> **Ctrl+Alt+[ 捕捉想法 · Ctrl+Alt+] 用户后台 · 白/灰/青轻质美学**

## 用户使用（推荐）

从 [Releases](../../releases) 下载 `IdeaWeaver-Setup.msi`，安装即用：

1. 首次打开 → 点 ⚙ 配置模型 API Key（支持 DeepSeek / OpenAI / Ollama 本地 / 自定义 OpenAI 兼容）
2. 系统托盘常驻，左键切换后台
3. `Ctrl+Alt+[` 唤起输入浮窗，随时记录灵感
4. `Ctrl+Alt+]` 打开用户后台，查看想法 → 一键编织成设计文档

## 开发者

### 环境要求

- Python 3.11+ / Node.js 20+ / Rust stable
- 国内环境请先配镜像（见 CLAUDE.md）

### 快速开始

```bash
# 1. Python 后端
pip install -r requirements.txt
python run.py test        # 验证全链路（需先在 ~/.weaver/config.json 或 .env 配置 API Key）

# 2. 桌面壳开发
cd desktop && npm install && cd ..
cd desktop && .\node_modules\.bin\tauri.cmd dev
```

### 打包发布

```bash
# 后端 sidecar
scripts\build_backend.bat          # → dist/weaver-backend.exe

# 复制到 Tauri 并打包安装包
mkdir desktop\src-tauri\binaries
copy dist\weaver-backend.exe desktop\src-tauri\binaries\weaver-backend-x86_64-pc-windows-msvc.exe
cd desktop && npm run tauri build  # → target/release/bundle/msi/*.msi
```

推 `v*` tag 触发 GitHub Actions 自动打包 Release。

## 架构

```
Tauri 2 壳 (Rust, ~8MB)
├─ React 18 UI (WebView2)
│   ├─ CaptureOverlay   Ctrl+Alt+[ 输入浮窗
│   ├─ Dashboard        Ctrl+Alt+] 用户后台
│   └─ Settings         ⚙ 模型配置器
├─ 全局热键 + 系统托盘
└─ sidecar: weaver-backend.exe (PyInstaller)
    └─ FastAPI :8765
        ├─ Collector → Weaver → Architect → Critic  (Agent 流水线)
        ├─ Inquisitor (V2 追问) / Monitor (V3 自治)
        └─ SQLite + ChromaDB 持久化 (~/.weaver/data)
```

## 项目结构

```
src/              Python 后端 (agents/api/core/storage)
desktop/          Tauri 2 + React 桌面壳
DESIGN.md         完整设计文档 (19 章)
TRACEABILITY.md   设计→代码对照清单
CLAUDE.md         开发者指南 (镜像配置/命令/架构)
```
