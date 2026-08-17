@echo off
cd /d "%~dp0"
echo 850 SCOS — Data Engine
echo Collector - Processor - Storage - Publisher
echo.
python main.py --daemon
pause
