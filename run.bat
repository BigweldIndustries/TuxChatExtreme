@echo off
setlocal EnableDelayedExpansion

py -m pip install -r requirements.txt
python "main.py"

pause
exit /b 0