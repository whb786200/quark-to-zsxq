@echo off
setlocal
cd /d "%~dp0.."
"C:\Users\19586\.workbuddy\binaries\python\envs\default\Scripts\python.exe" "%~dp0run-nightly.py" %*
exit /b %errorlevel%
