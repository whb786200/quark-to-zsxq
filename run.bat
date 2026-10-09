@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   夸克网盘 → 知识星球 自动发布工具
echo ============================================
echo.

if "%1"=="" (
    echo 用法:
    echo   run.bat init          - 初始化配置
    echo   run.bat share         - 仅创建分享链接
    echo   run.bat publish       - 分享+发布到星球
    echo   run.bat batch         - 批量执行
    echo.
    set /p MODE=请选择模式 [init/share/publish/batch]: 
) else (
    set MODE=%1
)

if "%MODE%"=="init" (
    python main.py --init-config
) else if "%MODE%"=="share" (
    set /p FID=文件/文件夹ID: 
    set /p TITLE=标题: 
    python main.py --file-id %FID% --title "%TITLE%" --no-publish
) else if "%MODE%"=="publish" (
    set /p FID=文件/文件夹ID: 
    set /p TITLE=标题: 
    set /p GID=星球ID: 
    python main.py --file-id %FID% --title "%TITLE%" --group-id %GID%
) else if "%MODE%"=="batch" (
    set /p BATCH=批量任务JSON路径 [config/tasks.json]: 
    if "%BATCH%"=="" set BATCH=config/tasks.json
    python main.py --batch %BATCH%
) else (
    echo 未知模式: %MODE%
)

echo.
pause
