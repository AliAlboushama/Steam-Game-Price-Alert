@echo off
rem Windows: starts the bot with no window. It keeps checking until you log out or restart.
rem To start it automatically at login, put a shortcut to this file in shell:startup
rem To stop it: Task Manager > Details > end "pythonw.exe"
cd /d "%~dp0"
start "" pythonw main.py --daemon
