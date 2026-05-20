@echo off
cd /d "%~dp0"

:: ── DeepSeek 余额组件打包脚本 ──
:: 使用 Anaconda Python + PyInstaller
:: 必须排除 Anaconda 全家桶，否则 EXE 从 16MB 膨胀到 168MB

pyinstaller ^
    --onefile ^
    --windowed ^
    --name DeepSeekBalance ^
    --exclude-module numpy ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module jupyter ^
    --exclude-module sklearn ^
    --exclude-module torch ^
    --exclude-module tensorflow ^
    --collect-all customtkinter ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --hidden-import PIL.ImageFont ^
    main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo   BUILD SUCCESS!
    echo   EXE: dist\DeepSeekBalance.exe
    echo ============================================
) else (
    echo.
    echo ============================================
    echo   BUILD FAILED!
    echo ============================================
)

pause
