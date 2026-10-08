@echo off
rem nCore Scraper inditasa forrasbol, Python 3.12-vel
rem (a C:\Python313 serult, ezert nem a sima duplakattintas)
cd /d "%~dp0"
py -3.12 run_ncore.py
if errorlevel 1 pause
