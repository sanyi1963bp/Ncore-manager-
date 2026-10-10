from .common import *

class BookTableView(QTableView):
    """Egyedi táblázat:
    - Ctrl + bal klikk → megjelölés (hozzáadás)
    - Ctrl + jobb klikk → megjelölés törlése
    - Egérrel bekeretezés → megjelölés (hozzáadás)
    - Shift + Fel/Le/PgUp/PgDn → tartomány megjelölése (visszafelé lépve
      a tartományból kikerülő sorok jelölése is visszavonódik)
    - Shift + Home / Shift + End → megjelölés az oldal elejéig / végéig
    - Jobb gombbal végighúzás → a végighúzott sorok jelölésének törlése
    - Shift + jobb klikk → jelölés törlése az aktuális és a kattintott sor között
    - Sima jobb klikk → helyi menü (mint eddig)
    """

    SHIFT_NAV_KEYS = {Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown,
                      Qt.Key_Home, Qt.Key_End}

    def __init__(self, parent=None):
        super().__init__(parent)
        # Shift-es jelölés: a kiinduló sor és a kezdéskor már meglévő jelölések
        self._mark_anchor = None
        self._mark_base = None
        # Jobb gombos húzás (jelölés törlése)
        self._rdrag_start = None
        self._rdrag_base = None
        self._rdrag_moved = False
        self._suppress_menu = False

    # ---- Közös segédek ----
    def _nids_in_rows(self, row_a: int, row_b: int) -> Set[str]:
        """A két (proxy) sor közti tartomány ncore_id-i."""
        proxy = self.model()
        src_model = proxy.sourceModel()
        lo, hi = sorted((row_a, row_b))
        result = set()
        for r in range(max(0, lo), min(proxy.rowCount() - 1, hi) + 1):
            src_row = proxy.mapToSource(proxy.index(r, 0)).row()
            nid = str(src_model.books[src_row].get("ncore_id", ""))
            if nid:
                result.add(nid)
        return result

    def _unmark_range(self, base: Set[str], row_a: int, row_b: int):
        src_model = self.model().sourceModel()
        src_model.set_marked_ids(base - self._nids_in_rows(row_a, row_b))
        self._notify_parent()

    def keyPressEvent(self, event):
        if not (event.key() in self.SHIFT_NAV_KEYS
                and event.modifiers() & Qt.ShiftModifier):
            super().keyPressEvent(event)
            return

        proxy = self.model()
        rows = proxy.rowCount()
        if rows == 0:
            return
        cur = self.currentIndex()
        cur_row = cur.row() if cur.isValid() else 0
        col = cur.column() if cur.isValid() else 0
        src_model = proxy.sourceModel()
        if self._mark_anchor is None:
            self._mark_anchor = cur_row
            self._mark_base = set(src_model.marked_ids)

        # Új aktuális sor
        page = max(1, self.viewport().height() // max(1, self.rowHeight(cur_row)) - 1)
        new_row = {
            Qt.Key_Up: cur_row - 1,
            Qt.Key_Down: cur_row + 1,
            Qt.Key_PageUp: cur_row - page,
            Qt.Key_PageDown: cur_row + page,
            Qt.Key_Home: 0,
            Qt.Key_End: rows - 1,
        }[event.key()]
        new_row = max(0, min(rows - 1, new_row))
        new_idx = proxy.index(new_row, col)

        # Megjelölés: a kezdeti jelölések + a kiinduló és az aktuális sor közti tartomány
        lo, hi = sorted((self._mark_anchor, new_row))
        ids = set(self._mark_base)
        for r in range(lo, hi + 1):
            src_row = proxy.mapToSource(proxy.index(r, 0)).row()
            nid = str(src_model.books[src_row].get("ncore_id", ""))
            if nid:
                ids.add(nid)
        src_model.set_marked_ids(ids)

        self.selectionModel().setCurrentIndex(new_idx, QItemSelectionModel.NoUpdate)
        self.clearSelection()
        self.scrollTo(new_idx)
        self._notify_parent()
        event.accept()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            # Shift felengedve: a jelölés véglegesítve
            self._mark_anchor = None
            self._mark_base = None
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        self._mark_anchor = None
        self._mark_base = None
        super().focusOutEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        modifiers = event.modifiers()
        index = self.indexAt(event.position().toPoint())

        if index.isValid() and (modifiers & Qt.ControlModifier):
            # Ctrl + bal klikk → megjelölés
            if event.button() == Qt.LeftButton:
                src_model = self.model().sourceModel()
                src_index = self.model().mapToSource(index)
                src_model.mark_row(src_index.row())
                # Frissítjük a kijelöltek listáját a főablakban
                self._notify_parent()
                event.accept()
                return
            # Ctrl + jobb klikk → megjelölés törlése
            elif event.button() == Qt.RightButton:
                src_model = self.model().sourceModel()
                src_index = self.model().mapToSource(index)
                src_model.unmark_row(src_index.row())
                self._notify_parent()
                event.accept()
                return

        if (index.isValid() and event.button() == Qt.RightButton
                and not (modifiers & Qt.ControlModifier)):
            src_model = self.model().sourceModel()
            if modifiers & Qt.ShiftModifier:
                # Shift + jobb klikk → tartomány jelölésének törlése
                cur = self.currentIndex()
                start = cur.row() if cur.isValid() else index.row()
                self._unmark_range(set(src_model.marked_ids), start, index.row())
                self._suppress_menu = True
            else:
                # Jobb gombos húzás kezdete (ha nem mozdul, helyi menü lesz)
                self._rdrag_start = index.row()
                self._rdrag_base = set(src_model.marked_ids)
                self._rdrag_moved = False
                self._suppress_menu = False
            self.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._rdrag_start is not None and event.buttons() & Qt.RightButton:
            pos = event.position().toPoint()
            index = self.indexAt(pos)
            if not index.isValid():
                # Táblázaton kívül: első / utolsó sorig
                row = 0 if pos.y() < 0 else self.model().rowCount() - 1
            else:
                row = index.row()
            if row != self._rdrag_start:
                self._rdrag_moved = True
            if self._rdrag_moved:
                self._unmark_range(self._rdrag_base, self._rdrag_start, row)
                self.selectionModel().setCurrentIndex(
                    self.model().index(row, max(0, self.currentIndex().column())),
                    QItemSelectionModel.NoUpdate)
                self.scrollTo(self.model().index(row, 0))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Egérrel bekeretezés (rubberband) után a kijelölt sorokat megjelöljük."""
        if event.button() == Qt.RightButton and self._rdrag_start is not None:
            if self._rdrag_moved:
                self._suppress_menu = True   # húzás volt, ne jöjjön helyi menü
            self._rdrag_start = None
            self._rdrag_base = None
            self._rdrag_moved = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

        # Ha volt kiválasztás húzással (nem Ctrl), megjelöljük a kiválasztott sorokat
        if (event.button() == Qt.LeftButton
                and not (event.modifiers() & Qt.ControlModifier)):
            sel_indexes = self.selectionModel().selectedRows()
            if len(sel_indexes) > 1:  # Csak húzásnál (több sor)
                src_model = self.model().sourceModel()
                for idx in sel_indexes:
                    src_idx = self.model().mapToSource(idx)
                    src_model.mark_row(src_idx.row())
                self.clearSelection()
                self._notify_parent()

    def wheelEvent(self, event):
        # Ctrl + görgő → a táblázat saját betűmérete
        if event.modifiers() & Qt.ControlModifier:
            win = self.window()
            if hasattr(win, "change_table_font"):
                win.change_table_font(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)

    def viewportEvent(self, event):
        # Jobb gombos húzás / Shift + jobb klikk után ne nyíljon helyi menü
        if event.type() == QEvent.ContextMenu and self._suppress_menu:
            self._suppress_menu = False
            event.accept()
            return True
        return super().viewportEvent(event)

    def _notify_parent(self):
        """Értesíti a MainWindow-t a megjelölések változásáról."""
        win = self.window()
        if hasattr(win, 'update_marked_list'):
            win.update_marked_list()


# ====================== SCRAPER WORKER ======================
