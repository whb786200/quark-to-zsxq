@echo off
setlocal
cd /d "%~dp0"
python -X utf8 daily_quark_plan.py --folder "自发群" --destination "工程交流2群（筑界）" --limit 100 --slot auto %*
endlocal
