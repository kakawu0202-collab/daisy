@echo off
rem 850 SCOS — DEV environment (console mode)
rem Ports: Portal 5051 | Engine 8701 | Control 8901  — 与线上 5050/8700/8900 隔离
cd /d "%~dp0"
set SCOS_PORTAL_PORT=5051
set SCOS_ENGINE_PORT=8701
set SCOS_CONTROL_PORT=8901
set YUMIN_URL=http://localhost:5051/sync
echo 850 SCOS — DEV Portal
echo http://localhost:5051
echo.
cd portal
python main.py
pause
