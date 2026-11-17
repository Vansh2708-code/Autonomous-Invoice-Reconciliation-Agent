@echo off
title Autoro - Financial Operations GUI
cd /d "%~dp0autoro"
echo Starting Autoro GUI server at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
