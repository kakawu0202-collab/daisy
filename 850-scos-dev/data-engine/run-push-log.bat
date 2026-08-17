@echo off
cd /d "%~dp0"
python -c "from scheduler import run; run()"
pause
