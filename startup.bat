@echo off
REM Run the app from the project folder
cd /d "%~dp0"
pip install -r requirements.txt
python.exe ".\main.py"

REM If python is not on PATH, replace the line above with a full path:
REM "C:\Users\ASUS\AppData\Local\Programs\Python\Python311\python.exe" main.py
