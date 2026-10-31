@echo off
rem 3_onepiece: python gauges\tomorrow.py onepiece on the realistic run (capability_real). See README.txt.
cd /d "%~dp0.."
set SCORPION_CAP=capability_real
python gauges\tomorrow.py onepiece
echo.
pause
