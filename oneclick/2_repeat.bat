@echo off
rem 2_repeat: python gauges\tomorrow.py repeat on the realistic run (capability_real). See README.txt.
cd /d "%~dp0.."
set SCORPION_CAP=capability_real
python gauges\tomorrow.py repeat
echo.
pause
