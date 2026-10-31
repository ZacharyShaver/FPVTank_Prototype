@echo off
rem 0_status: python gauges\tomorrow.py status on the realistic run (capability_real). See README.txt.
cd /d "%~dp0.."
set SCORPION_CAP=capability_real
python gauges\tomorrow.py status
echo.
pause
