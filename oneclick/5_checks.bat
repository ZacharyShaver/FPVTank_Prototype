@echo off
rem 5_checks: python gauges\tomorrow.py checks on the realistic run (capability_real). See README.txt.
cd /d "%~dp0.."
set SCORPION_CAP=capability_real
python gauges\tomorrow.py checks
echo.
pause
