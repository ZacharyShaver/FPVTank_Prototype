@echo off
rem 1_results: python gauges\tomorrow.py results on the realistic run (capability_real). See README.txt.
cd /d "%~dp0.."
set SCORPION_CAP=capability_real
python gauges\tomorrow.py results
echo.
pause
