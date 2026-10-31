@echo off
rem 4_film: python gauges\tomorrow.py film on the realistic run (capability_real). See README.txt.
cd /d "%~dp0.."
set SCORPION_CAP=capability_real
python gauges\tomorrow.py film
echo.
pause
