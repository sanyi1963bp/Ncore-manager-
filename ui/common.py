import sys
import os
from datetime import datetime
from typing import List, Dict, Set
from urllib.parse import quote_plus

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QDockWidget, QTableView, QLabel, QPushButton, QLineEdit,
    QComboBox, QStatusBar, QMenuBar, QMessageBox, QProgressBar,
    QAbstractItemView, QStyledItemDelegate, QToolBar,
    QFrame, QDialog, QFormLayout, QTabWidget, QCheckBox, QTextEdit,
    QSpinBox, QSlider, QMenu, QSizePolicy, QListWidget, QListWidgetItem,
    QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QTimer, QAbstractTableModel, QThread, Signal, QUrl, QEvent, QItemSelectionModel
from PySide6.QtGui import (
    QPixmap, QMouseEvent, QColor, QBrush, QDesktopServices,
    QFont, QFontMetrics, QKeySequence, QShortcut, QKeyEvent
)

import gui_config
from layout_state import get_layout_state, init_layout_state
from database import (
    search_books, count_books, get_formats, init_database, update_book_field,
    create_backup, list_backups, restore_backup, delete_backup
)
from downloader import Downloader
from scraper import Scraper
import config

# Érvényes e-book és szöveg formátumok
VALID_FORMATS = {
    "epub", "pdf", "mobi", "azw", "azw3", "fb2", "lit",
    "txt", "rtf", "doc", "docx", "odt", "djvu", "cbr", "cbz",
}

# Oszlopok, amelyeknél a helyi menüben keresés is elérhető
SEARCHABLE_COLUMNS = {"ncore_id", "szerzo", "cim", "sorozat"}

# Megjelölés színei
MARK_BG = QColor("#2d7a3a")
MARK_FG = QColor("#ffffff")

# Nem szerkeszthető oszlopok (csak olvasható)
READONLY_COLUMNS = {"ncore_id", "feltoltve_datum"}


# ====================== TABLE MODEL ======================

NCORE_DETAIL_URL = "https://ncore.pro/torrents.php?action=details&id={ncore_id}"
# Moly.hu keresés URL sablon (magyar könyvkatalógus, ismertetők, vásárlás)
MOLY_SEARCH_URL = "https://moly.hu/kereses?utf8=%E2%9C%93&q={query}"




# Shared GUI font limits used by the main window and settings dialog.
FONT_MIN = 7
FONT_MAX = 28
FONT_DEFAULT = 10
