@echo off
rem 850 SCOS — DEV Data Engine (console mode, push to local dev portal :5051)
cd /d "%~dp0"
set SCOS_ENGINE_PORT=8701
set YUMIN_URL=http://localhost:5051/sync
echo 850 SCOS — DEV Data Engine (daemon)
echo trigger: http://localhost:8701/trigger  |  status: http://localhost:8701/status
echo push target: %YUMIN_URL%
echo.
cd data-engine
python main.py --daemon
pause
