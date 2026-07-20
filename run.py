"""Idea Weaver 一键启动
用法:
  python run.py server    → 仅 API 服务
  python run.py desktop   → 桌面模式 (当前: Tkinter 浮窗)
  python run.py tauri     → Tauri 2 + React 桌面壳 (需先装 Rust + npm install)
  python run.py test      → 全链路验证
"""

import os, sys, asyncio

# API Key: 用户自己配置 ~/.weaver/config.json 或 .env

MODE = sys.argv[1] if len(sys.argv) > 1 else "server"


def run_server():
    print("Idea Weaver API: http://localhost:8765")
    print("Swagger: http://localhost:8765/docs")
    import uvicorn
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8765, log_level="info")


def run_desktop():
    print("Starting Idea Weaver...")
    from src.main import main
    main()


async def run_test():
    print("=== Idea Weaver Pipeline Test (DeepSeek V4) ===\n")
    from src.core.deepseek_service import DeepSeekService
    from src.agents.collector import CollectorAgent
    from src.agents.weaver import WeaverAgent
    from src.agents.architect import ArchitectAgent
    from src.agents.critic import CriticAgent
    from src.core.models import SourceType

    llm = DeepSeekService()

    print("1. Collector...")
    node = await CollectorAgent(llm).process(
        "微服务调用太慢需要缓存，像高速公路分快慢车道", SourceType.TEXT)
    print(f"   OK: {node.standardized_content[:80]}...")

    print("2. Weaver...")
    result = await WeaverAgent(llm).weave([node], "高性能缓存系统设计")
    clusters = WeaverAgent.build_clusters_from_result(result, [node])
    rels = WeaverAgent.build_relationships(result, [node])
    print(f"   OK: {len(clusters)} clusters, {len(rels)} rels")

    print("3. Architect...")
    design = await ArchitectAgent(llm).design(clusters, rels, [], [], "高性能缓存系统设计")
    print(f"   OK: {len(design.content_markdown)} chars")

    print("4. Critic...")
    fb = await CriticAgent(llm).critique(design, [node])
    print(f"   OK: approved={fb.approved} coherence={fb.scores.coherence:.2f} feasibility={fb.scores.feasibility:.2f}")

    from src.storage.file_store import FileStore
    path = FileStore().save_design_markdown(design.content_markdown, "高性能缓存系统", "2026-07-19")
    print(f"\nSaved: {path}")
    print("=" * 50)
    print("ALL TESTS PASSED")


def run_tauri():
    """Tauri 2 + React 桌面壳 —— 先启动 Python 后端, 再启动 Tauri"""
    import subprocess, time, os

    # 找到 cargo (Rust 刚装完可能不在 PATH)
    cargo_bin = os.path.expanduser("~/.cargo/bin")
    env = {**os.environ, "PATH": os.environ["PATH"] + os.pathsep + cargo_bin}

    print("Starting Python backend...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.server:app",
         "--host", "127.0.0.1", "--port", "8765", "--log-level", "error"],
        cwd=".",
    )
    time.sleep(3)
    print("Python backend ready. Starting Tauri dev server...")
    # 用 node_modules 的 tauri CLI (预编译二进制)
    tauri_cmd = os.path.abspath(os.path.join("desktop", "node_modules", ".bin", "tauri.cmd"))
    subprocess.run([tauri_cmd, "dev"], cwd="desktop", env=env)
    proc.terminate()


if __name__ == "__main__":
    if MODE == "server":
        run_server()
    elif MODE == "test":
        asyncio.run(run_test())
    elif MODE == "desktop":
        run_desktop()
    elif MODE == "tauri":
        run_tauri()
    else:
        run_server()
