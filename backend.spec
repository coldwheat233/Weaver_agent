# Idea Weaver Backend — PyInstaller 打包规格
# 用法: pyinstaller backend.spec

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 需要打包的数据文件
datas = [
    ("data/schema.sql", "data"),
    ("src/agents/prompts", "src/agents/prompts"),
    ("src/ui/static", "src/ui/static"),
    ("skills", "skills"),
]

a = Analysis(
    ["src/server_entry.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "sqlalchemy.dialects.sqlite.aiosqlite",
        "aiosqlite",
        "httpx",
        "loguru",
        "pydantic_settings",
        "yaml",
        "networkx",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # 桌面组件不打包 (Tauri 负责 UI)
        "pywebview", "webview", "pystray", "pynput", "keyboard",
        "PIL", "tkinter", "_tkinter",
        # 重型可选依赖 (懒装)
        "whisper", "torch", "torchaudio", "chromadb",
        "numpy", "pandas", "scipy", "matplotlib",
        # 未使用的
        "litellm", "langchain", "langgraph",
        "notebook", "IPython",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="weaver-backend",
    debug=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
)
