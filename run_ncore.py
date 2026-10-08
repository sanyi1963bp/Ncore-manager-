#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_ncore.py
============
Indító szkript a nCore Scraper GUI-hoz (Main_window.py).
PyInstaller --onedir módhoz optimalizálva.

A sys.frozen ellenőrzés gondoskodik róla, hogy az exe mellé
kerüljön a munkakönyvtár, így a config.json, boritok/, *.db
helyesen relatív elérési úttal találhatók.
"""

import sys
import os

# Ha PyInstaller csomagból fut: exe könyvtárára állj
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from PySide6.QtWidgets import QApplication
from Main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
