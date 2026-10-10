@echo off
cd /d "%~dp0"
echo Mappa: %CD%
echo.
if not exist "run_ncore.py" echo HIBA: nincs run_ncore.py
if not exist "main_window.py" echo HIBA: nincs main_window.py
if not exist "ui\table_model.py" echo HIBA: nincs ui\table_model.py
if not exist "core\scraper.py" echo HIBA: nincs core\scraper.py
echo.
py -3.12 run_ncore.py
if errorlevel 1 pause
