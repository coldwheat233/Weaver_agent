@echo off
REM ========================================
REM  Idea Weaver Windows .exe 构建脚本
REM ========================================

echo === Idea Weaver Build ===
echo.

REM 1. 安装依赖
echo [1/4] Installing dependencies...
pip install -r requirements.txt -q

REM 2. 运行测试
echo [2/4] Running tests...
python -m pytest tests/ -v --tb=short
if %errorlevel% neq 0 (
    echo TESTS FAILED. Aborting build.
    exit /b 1
)

REM 3. 生成图标
echo [3/4] Generating icon...
python scripts/generate_icon.py

REM 4. PyInstaller 打包
echo [4/4] Building .exe...
pyinstaller pyinstaller.spec --clean --noconfirm

echo.
echo === Build complete ===
echo Output: dist/IdeaWeaver.exe
