#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stabil indító a refaktorált nCore Scraperhez."""
import os
import sys
from pathlib import Path

# Mindig a run_ncore.py valódi könyvtára legyen az importálási alap.
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)

# PyInstaller esetén is az EXE könyvtárából dolgozunk.
if getattr(sys, "frozen", False):
    os.chdir(Path(sys.executable).resolve().parent)

from PySide6.QtWidgets import QApplication
from ncore_main_window_impl import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
