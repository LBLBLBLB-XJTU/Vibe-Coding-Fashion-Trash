@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   SysGauge — 系统托盘组件 打包工具
echo ========================================
echo.

pip show psutil >nul 2>&1 || pip install psutil
pip show pystray >nul 2>&1 || pip install pystray

echo [*] 开始打包...
pyinstaller --onefile --windowed --noconsole ^
    --name "SysGauge" ^
    --hidden-import psutil ^
    --hidden-import pystray ^
    --exclude-module numpy ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module jupyter ^
    --exclude-module IPython ^
    --exclude-module sklearn ^
    --exclude-module torch ^
    --exclude-module tensorflow ^
    --clean ^
    system_widget.py

echo.
echo ========================================
echo   ✅ 完成！EXE: dist\SysGauge.exe
echo ========================================
pause
