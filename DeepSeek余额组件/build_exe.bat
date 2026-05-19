@echo off
chcp 65001 >nul
title DeepSeek 余额小组件 - 构建打包

echo ============================================
echo   DeepSeek 余额小组件 - 打包工具
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [✓] Python 已检测到
python --version

:: 安装依赖
echo.
echo [1/3] 正在安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [✓] 依赖安装完成

:: PyInstaller 打包
echo.
echo [2/3] 正在打包为 EXE（首次打包可能需要 1-3 分钟）...
pyinstaller --onefile --windowed ^
    --name "DeepSeekBalance" ^
    --icon NONE ^
    --add-data "deepseek_api.py;." ^
    --add-data "config.py;." ^
    --add-data "widget.py;." ^
    --hidden-import customtkinter ^
    --hidden-import requests ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import PIL._tkinter_finder ^
    --clean ^
    main.py

if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)
echo [✓] 打包完成

:: 复制到桌面目录
echo.
echo [3/3] 正在复制到桌面...
copy /Y "dist\DeepSeekBalance.exe" ".\DeepSeekBalance.exe" >nul
echo [✓] EXE 已生成: DeepSeekBalance.exe

echo.
echo ============================================
echo   打包成功！
echo   文件位置: %cd%\DeepSeekBalance.exe
echo   直接双击 DeepSeekBalance.exe 即可运行
echo ============================================

:: 清理临时文件
rd /s /q build >nul 2>&1
rd /s /q dist >nul 2>&1
del /f /q main.spec >nul 2>&1

pause
