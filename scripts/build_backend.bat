@echo off
REM === Idea Weaver 后端打包 (PyInstaller sidecar) ===
echo [1/2] Installing PyInstaller...
pip install pyinstaller -q -i https://mirrors.aliyun.com/pypi/simple/

echo [2/2] Building weaver-backend.exe...
pyinstaller backend.spec --clean --noconfirm

if exist dist\weaver-backend.exe (
    echo.
    echo === SUCCESS ===
    for %%I in (dist\weaver-backend.exe) do echo Output: dist\weaver-backend.exe (%%~zI bytes)

    echo.
    echo Copying to Tauri binaries...
    if not exist desktop\src-tauri\binaries mkdir desktop\src-tauri\binaries
    copy /Y dist\weaver-backend.exe desktop\src-tauri\binaries\weaver-backend-x86_64-pc-windows-msvc.exe
    echo Done. Next: cd desktop ^&^& npm run tauri build
) else (
    echo BUILD FAILED
    exit /b 1
)
