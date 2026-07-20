# PyInstaller 打包规格 —— 单 .exe Windows 桌面应用
# 用法: pyinstaller pyinstaller.spec

import sys
from pathlib import Path

block_cipher = None

SRC_DIR = Path("src")

added_files = [
    ("data/schema.sql", "data"),
    ("skills/*.md", "skills"),
    (str(SRC_DIR / "ui" / "static"), "src/ui/static"),
    (str(SRC_DIR / "ui" / "templates"), "src/ui/templates"),
    (str(SRC_DIR / "agents" / "prompts"), "src/agents/prompts"),
]

a = Analysis(
    [str(SRC_DIR / "main.py")],
    pathex=[".", "src"],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "pystray", "pynput", "webview", "PIL",
        "chromadb", "sqlalchemy", "aiosqlite",
        "langgraph", "langgraph.checkpoint.sqlite",
        "litellm", "networkx", "loguru",
        "pydantic", "pydantic_settings",
        "uvicorn", "fastapi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "pandas", "numpy",
        "scipy", "notebook", "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    name="IdeaWeaver",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # 无控制台窗口（桌面应用）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="weaver.ico",       # 需要制作一个图标文件
)
