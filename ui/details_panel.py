from .common import *
from .cover_label import CoverLabel

class DetailsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ls = get_layout_state()
        min_w = min(self.ls.get("jobb_panel", "min_szelesseg", default=180), 180)
        self.setMinimumWidth(min_w)
        self.setup_ui()
        # Saját betűméret (None = a főablakét követi)
        self.font_size = self.ls.get("jobb_panel", "betumeret")
        if self.font_size:
            self.set_font_size(self.font_size)
        else:
            main_size = gui_config.get_config().get("font", "size", default=10)
            self.lbl_font.setText(f"{main_size} pt")

    # ---- Saját betűméret: A− / A+ gombok vagy Ctrl + egérgörgő ----
    def set_font_size(self, size: int):
        size = max(7, min(28, int(size)))
        self.font_size = size
        self.setStyleSheet(f"QWidget {{ font-size: {size}pt; }}")
        self.lbl_font.setText(f"{size} pt")
        self.ls.set("jobb_panel", "betumeret", size)

    def change_font_size(self, delta: int):
        current = self.font_size or gui_config.get_config().get("font", "size", default=10)
        self.set_font_size(current + delta)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.change_font_size(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
        else:
            super().wheelEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
            self.wheelEvent(event)
            return True
        return super().eventFilter(obj, event)

    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        # Betűméret-vezérlő a panel tetején
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Betűméret:"))
        btn_smaller = QPushButton("A−")
        btn_bigger = QPushButton("A+")
        for btn, d in ((btn_smaller, -1), (btn_bigger, 1)):
            btn.setFixedWidth(44)
            btn.setToolTip("Betűméret ebben a panelben (Ctrl + egérgörgő is működik)")
            btn.clicked.connect(lambda _=False, d=d: self.change_font_size(d))
            font_row.addWidget(btn)
        self.lbl_font = QLabel("")
        font_row.addWidget(self.lbl_font)
        font_row.addStretch()
        outer.addLayout(font_row)

        # Borító fent, adatok lent; a kettő közti elválasztó húzható
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        outer.addWidget(self.splitter)

        self.cover_label = CoverLabel()
        self.splitter.addWidget(self.cover_label)

        # Középső rész: szerző, cím, linkek (görgethető, ha kevés a hely)
        bottom = QWidget()
        layout = QVBoxLayout(bottom)
        layout.setContentsMargins(0, 6, 0, 0)
        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setFrameShape(QFrame.NoFrame)
        info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        info_scroll.setWidget(bottom)
        info_scroll.viewport().installEventFilter(self)  # Ctrl + görgő itt is
        self.splitter.addWidget(info_scroll)

        info = QFrame()
        info_layout = QVBoxLayout(info)
        self.lbl_author = QLabel("Szerző: -")
        self.lbl_title = QLabel("Cím: -")
        for lbl in (self.lbl_author, self.lbl_title):
            lbl.setWordWrap(True)
            info_layout.addWidget(lbl)
        layout.addWidget(info)

        # ---- Linkek ----
        link_style = (
            "QLabel a { color: #5dade2; text-decoration: none; }"
            "QLabel a:hover { text-decoration: underline; }"
            "QLabel { padding: 2px 0; }"
        )

        self.link_ncore = QLabel()
        self.link_ncore.setStyleSheet(link_style)
        self.link_ncore.setTextFormat(Qt.RichText)
        self.link_ncore.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.link_ncore.linkActivated.connect(self._open_url)
        layout.addWidget(self.link_ncore)

        self.link_moly = QLabel()
        self.link_moly.setStyleSheet(link_style)
        self.link_moly.setTextFormat(Qt.RichText)
        self.link_moly.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.link_moly.linkActivated.connect(self._open_url)
        layout.addWidget(self.link_moly)

        layout.addStretch()

        # Alsó rész: leírás
        desc_box = QWidget()
        layout = QVBoxLayout(desc_box)
        layout.setContentsMargins(0, 6, 0, 0)
        self.splitter.addWidget(desc_box)
        self.splitter.setSizes([360, 150, 300])

        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        # Ctrl + görgő itt is a panel betűméretét állítsa (ne a QTextEdit saját zoomját)
        self.desc_text.viewport().installEventFilter(self)
        layout.addWidget(QLabel("<b>Tartalom:</b>"))
        layout.addWidget(self.desc_text, 1)

    def _open_url(self, url: str):
        """Megnyitja az URL-t az alapértelmezett böngészőben."""
        QDesktopServices.openUrl(QUrl(url))

    def update_info(self, book: dict):
        self.lbl_author.setText(f"<b>Szerző:</b> {book.get('szerzo', '-')}")
        self.lbl_title.setText(f"<b>Cím:</b> {book.get('cim', '-')}")
        self.desc_text.setPlainText(book.get("leiras", "Nincs leírás"))

        # Borító
        self.cover_label.set_cover(book.get("kep_utvonal"))

        # nCore link
        ncore_id = book.get("ncore_id", "")
        if ncore_id:
            url = NCORE_DETAIL_URL.format(ncore_id=ncore_id)
            self.link_ncore.setText(
                f'🌐 <a href="{url}">Torrent oldala az nCore-on</a>'
            )
        else:
            self.link_ncore.setText("")

        # Moly.hu keresés (szerző + cím alapján)
        cim = book.get("cim", "")
        szerzo = book.get("szerzo", "")
        if cim:
            search_term = f"{szerzo} {cim}".strip() if szerzo else cim
            url = MOLY_SEARCH_URL.format(query=quote_plus(search_term))
            self.link_moly.setText(
                f'📚 <a href="{url}">Keresés a Moly.hu-n</a>'
            )
        else:
            self.link_moly.setText("")

    def clear(self):
        self.cover_label.set_cover(None)
        self.lbl_author.setText("Szerző: -")
        self.lbl_title.setText("Cím: -")
        self.link_ncore.setText("")
        self.link_moly.setText("")
        self.desc_text.clear()


# ====================== MAIN WINDOW ======================
