@echo off
rem 850 SCOS — AI Assistant（网页聊天版）
rem 依赖：Service Layer（dev Portal 5051）运行中 + ai-engine/.env 已配置 LLM key
cd /d "%~dp0"
start http://localhost:5099
cd ai-engine
python web.py
pause
