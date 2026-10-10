@echo off
setlocal
cd /d "%~dp0"
py -3.12 run_ncore.py
if errorlevel 1 (
    echo.
    echo A program inditasa hibaval leallt.
    pause
)
endlocal
