@echo off
cls

echo.
echo  =========================================
echo   nCore Scraper -- EXE Builder
echo  =========================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [HIBA] Python nem talalhato!
    echo        https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Csomagok telepitese...
pip install --quiet --upgrade pyinstaller PySide6 requests beautifulsoup4
if errorlevel 1 (
    echo [HIBA] pip sikertelen!
    pause
    exit /b 1
)
echo [OK] Csomagok rendben.
echo.

echo [2/4] Build indul: nCore_Scraper.exe
echo.
pyinstaller --onedir --windowed --name nCore_Scraper --icon adatbazis.ico --noconfirm --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --hidden-import PySide6.QtNetwork --hidden-import bs4 --hidden-import requests --collect-submodules PySide6 run_ncore.py
if errorlevel 1 (
    echo.
    echo [HIBA] PyInstaller build sikertelen!
    pause
    exit /b 1
)
echo.
echo [OK] Build kesz.
echo.

echo [3/4] Adatfajlok masolasa a dist\nCore_Scraper\ mappaba...
if exist "config.json"       copy /Y "config.json"       "dist\nCore_Scraper\" >nul
if exist "ncore_konyvtar.db" copy /Y "ncore_konyvtar.db" "dist\nCore_Scraper\" >nul
if exist "gui_config.json"   copy /Y "gui_config.json"   "dist\nCore_Scraper\" >nul
if exist "boritok"           xcopy /E /I /Q /Y "boritok" "dist\nCore_Scraper\boritok\" >nul
echo [OK] Adatfajlok masolva.
echo.

echo [4/4] Takaritas...
rmdir /s /q build 2>nul
del /q nCore_Scraper.spec 2>nul
echo [OK] Takaritas kesz.
echo.

echo  =========================================
echo   KESZ!
echo   Futtathato mappa: dist\nCore_Scraper\
echo   Exe:  dist\nCore_Scraper\nCore_Scraper.exe
echo.
echo   FONTOS: az egesz dist\nCore_Scraper\
echo   mappatat kell atavinni, nem csak az exe-t!
echo  =========================================
echo.
pause
