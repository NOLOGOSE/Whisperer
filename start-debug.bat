@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
python voice_input.py
pause
