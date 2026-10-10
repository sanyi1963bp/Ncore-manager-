from .common import *

class BookTableModel(QAbstractTableModel):
    """Táblázat modell saját megjelölési rendszerrel.

    A marked_ids halmazban tárolt ncore_id-jú sorok zöld hátteret kapnak.
    Ez független a QTableView kiválasztásától, tehát tartósan megmarad.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.books: List[Dict] = []
        self.columns = []
        self.marked_ids: Set[str] = set()
        self.filtered_columns: Set[str] = set()   # oszlopszűrős oszlopok (🔍 a fejlécben)

    def rowCount(self, parent=None):
        return len(self.books)

    def columnCount(self, parent=None):
        return len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.books):
            return None
        book = self.books[index.row()]
        col = self.columns[index.column()]

        if role == Qt.DisplayRole:
            val = book.get(col["name"], "")
            if col["name"] == "feltoltve_datum" and val:
                try:
                    return datetime.strptime(val, "%Y-%m-%d %H:%M:%S").strftime("%y-%m-%d")
                except Exception:
                    return val
            return str(val or "")

        if role == Qt.BackgroundRole:
            nid = str(book.get("ncore_id", ""))
            if nid in self.marked_ids:
                return QBrush(MARK_BG)
            return None

        if role == Qt.ForegroundRole:
            nid = str(book.get("ncore_id", ""))
            if nid in self.marked_ids:
                return QBrush(MARK_FG)
            return None

        if role == Qt.UserRole:
            return book

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            col = self.columns[section]
            if col["name"] in self.filtered_columns:
                return f"🔍 {col['label']}"
            return col["label"]
        return None

    def flags(self, index):
        """Cellák szerkeszthetősége.
        
        Csak olvasható: ncore_id, feltoltve_datum.
        Minden más oszlop szerkeszthető dupla kattintással.
        """
        base = super().flags(index)
        if not index.isValid():
            return base
        col = self.columns[index.column()]
        if col["name"] in READONLY_COLUMNS:
            return base  # Csak olvasható
        return base | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
        """Cella szerkesztése és mentése az adatbázisba."""
        if role != Qt.EditRole or not index.isValid():
            return False

        row = index.row()
        col_idx = index.column()
        if row >= len(self.books) or col_idx >= len(self.columns):
            return False

        col_name = self.columns[col_idx]["name"]
        if col_name in READONLY_COLUMNS:
            return False

        book = self.books[row]
        ncore_id = str(book.get("ncore_id", ""))
        if not ncore_id:
            return False

        new_value = str(value).strip()
        old_value = str(book.get(col_name, "") or "")

        # Ha nem változott, nem csinálunk semmit
        if new_value == old_value:
            return False

        # Mentés az adatbázisba
        if update_book_field(ncore_id, col_name, new_value):
            # Memóriában is frissítjük
            book[col_name] = new_value
            self.dataChanged.emit(index, index)
            return True

        return False

    def set_books(self, books: List[Dict]):
        self.beginResetModel()
        self.books = books
        self.endResetModel()

    def toggle_mark(self, row: int) -> bool:
        """Megjelölés ki/be váltása. Visszaadja az új állapotot (True=megjelölt)."""
        if row < 0 or row >= len(self.books):
            return False
        nid = str(self.books[row].get("ncore_id", ""))
        if not nid:
            return False
        if nid in self.marked_ids:
            self.marked_ids.discard(nid)
            result = False
        else:
            self.marked_ids.add(nid)
            result = True
        # Frissítjük a sor megjelenítését
        left = self.index(row, 0)
        right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(left, right)
        return result

    def mark_row(self, row: int):
        """Sor megjelölése (hozzáadás)."""
        if row < 0 or row >= len(self.books):
            return
        nid = str(self.books[row].get("ncore_id", ""))
        if nid and nid not in self.marked_ids:
            self.marked_ids.add(nid)
            left = self.index(row, 0)
            right = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(left, right)

    def unmark_row(self, row: int):
        """Sor megjelölésének törlése."""
        if row < 0 or row >= len(self.books):
            return
        nid = str(self.books[row].get("ncore_id", ""))
        if nid and nid in self.marked_ids:
            self.marked_ids.discard(nid)
            left = self.index(row, 0)
            right = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(left, right)

    def clear_marks(self):
        """Minden megjelölés törlése."""
        self.marked_ids.clear()
        if self.books:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1)
            )

    def set_marked_ids(self, ids):
        """Megjelöltek halmazának cseréje (tömeges jelöléshez)."""
        self.marked_ids = set(ids)
        if self.books:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1)
            )

    def get_marked_books(self) -> List[Dict]:
        """Megjelölt könyvek listája."""
        return [b for b in self.books if str(b.get("ncore_id", "")) in self.marked_ids]


# ====================== CUSTOM TABLE VIEW ======================
