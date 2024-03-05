@echo off
set mutexname=pipe_mutex

REM Check if mutex already exists
tasklist /FI "WINDOWTITLE eq %mutexname%" 2>NUL | find /I /N "%mutexname%">NUL
if "%ERRORLEVEL%"=="0" echo Script is already running & exit

REM Create mutex
start "pipe_mutex" cmd /c "pause"

call .\venv\Scripts\activate.bat
python main.py

REM Close mutex
taskkill /FI "WINDOWTITLE eq %mutexname%" /F /T