"""Main application window for the refactored nCore eBook Manager."""
from ui.common import *
from ui.table_model import BookTableModel
from ui.table_view import BookTableView
from ui.scraper_worker import ScraperWorker
from ui.settings_dialog import SettingsDialog
from ui.cover_label import CoverLabel
from ui.details_panel import DetailsPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_database()
        gui_config.init_config()
        self.config_gui = gui_config.get_config()
        self.ls = init_layout_state()

        self.downloader = Downloader(log_callback=self.log)
        self.worker = None

        self.use_cache = self.ls.get("altalanos", "cache_hasznalat", default=True)
        self.full_cache: List[Dict] = []

        self.order_by = self.ls.get("altalanos", "rendezes_oszlop", default="feltoltve_datum")
        self.desc = self.ls.get("altalanos", "rendezes_csokkeno", default=True)
        self.page_size = self.ls.get("lapozas", "oldalmeret", default=100)
        self.current_page = 0
        self.total_count = 0

        self.setup_ui()
        self.load_columns_from_state()
        self.reload_cache()
        self.refresh_data(reset_page=True)

        QTimer.singleShot(300, self.apply_saved_sizes)
        QTimer.singleShot(500, self._check_credentials)

    def log(self, msg: str):
        self.statusBar().showMessage(msg, 5000)
        if hasattr(self, 'log_text') and self.log_text.isVisible():
            self.log_text.append(msg)
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )

    def _check_credentials(self):
        """Ha nincs felhasználónév vagy jelszó, megnyitjuk a beállításokat."""
        cfg = config.load_config()
        if not cfg.get("username") or not cfg.get("password"):
            QMessageBox.information(
                self, "Első indítás",
                "Üdvözöllek! A használathoz add meg az nCore\n"
                "felhasználónevedet és jelszavadat a Beállításokban."
            )
            self.show_settings()

    # ======================== UI FELÉPÍTÉS ========================
    def setup_ui(self):
        self.setWindowTitle("nCore eBook Manager")
        self.setStyleSheet(self.config_gui.generate_stylesheet())

        w = self.ls.get("foablak", "szelesseg", default=1780)
        h = self.ls.get("foablak", "magassag", default=1080)
        x = self.ls.get("foablak", "x_pozicio", default=100)
        y = self.ls.get("foablak", "y_pozicio", default=50)
        self.resize(w, h)
        self.move(x, y)
        if self.ls.get("foablak", "maximalizalt", default=False):
            self.showMaximized()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

        # ---- Központi rész ----
        central = QWidget()
        cl = QVBoxLayout(central)

        self.table_view = BookTableView()
        self.table_view.setAlternatingRowColors(
            self.ls.get("tablazat", "valtakozo_sorok", default=True)
        )
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setSortingEnabled(False)
        self.table_view.setEditTriggers(
            QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )
        self.table_view.doubleClicked.connect(self.on_double_click)
        self.table_view.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        header = self.table_view.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_menu)
        # Oszlopok sorrendje fogd és vidd módszerrel
        header.setSectionsMovable(True)
        header.sectionMoved.connect(self._on_column_moved)
        self.column_filters: Dict[str, str] = {}   # oszlopnév → keresett szöveg

        self.model = BookTableModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.table_view.setModel(self.proxy)

        cl.addWidget(self.table_view, 1)

        # ---- CSÚSZKA ----
        slider_row = QWidget()
        sl_lay = QHBoxLayout(slider_row)
        sl_lay.setContentsMargins(10, 8, 10, 8)

        slider_h = self.ls.get("lapozas", "csuszka_magassag", default=38)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(1)
        self.slider.setMinimumHeight(slider_h)
        self.slider.setStyleSheet(self.ls.get_slider_stylesheet())
        self.slider.valueChanged.connect(self.slider_preview)
        self.slider.sliderReleased.connect(self.slider_released)
        sl_lay.addWidget(QLabel("📍 Oldal:"))
        sl_lay.addWidget(self.slider, 1)
        cl.addWidget(slider_row)

        # ---- LAPOZÁS ----
        nav = QWidget()
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(10, 8, 10, 8)
        for txt, slot in [
            ("⏮ Első", self.first_page),
            ("⏪", self.prev_page),
            ("⏩", self.next_page),
            ("⏭ Utolsó", self.last_page),
        ]:
            btn = QPushButton(txt)
            btn.clicked.connect(slot)
            nl.addWidget(btn)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.valueChanged.connect(self.spin_page_changed)
        nl.addWidget(self.page_spin)

        self.lbl_info = QLabel("0 / 0 (0 könyv)")
        nl.addWidget(self.lbl_info)

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500", "1000"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentTextChanged.connect(self.change_page_size)
        nl.addWidget(QLabel("   Oldalméret:"))
        nl.addWidget(self.page_size_combo)
        nl.addStretch()

        # Táblázat saját betűmérete
        nl.addWidget(QLabel("Táblázat betű:"))
        for txt, d in (("A−", -1), ("A+", 1)):
            btn = QPushButton(txt)
            btn.setFixedWidth(44)
            btn.setToolTip("A táblázat betűmérete (Ctrl + egérgörgő a táblázaton is működik)")
            btn.clicked.connect(lambda _=False, d=d: self.change_table_font(d))
            nl.addWidget(btn)
        self.lbl_table_font = QLabel("")
        nl.addWidget(self.lbl_table_font)

        # A lapozó- és csúszkasor ne szabja meg a középrész minimális
        # szélességét, különben a jobb panelt nem lehet szélesebbre húzni
        # (nagy betűméretnél a sor >1000 px). Szűk helyen jobbról levágódik.
        for row in (slider_row, nav):
            row.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            row.setMinimumWidth(0)

        cl.addWidget(nav)
        self.setCentralWidget(central)

        # ============ BAL OLDALI PANEL ============
        self.filter_dock = QDockWidget("Műveletek / Szűrés", self)
        # Nem bezárható: itt vannak a gombok (Beállítások is), bezárva nem
        # lehetne visszakapcsolni
        self.filter_dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.filter_dock.toggleViewAction().setEnabled(False)
        fw = QWidget()
        fl = QVBoxLayout(fw)
        fl.setContentsMargins(8, 8, 8, 8)
        fl.setSpacing(6)

        # Felső rész (Műveletek + Szűrés) görgethető dobozban, hogy
        # összébb húzva se nyomódjanak össze a gombok
        top_box = QWidget()
        tl = QVBoxLayout(top_box)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(6)
        top_scroll = QScrollArea()
        top_scroll.setWidgetResizable(True)
        top_scroll.setFrameShape(QFrame.NoFrame)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        top_scroll.setWidget(top_box)

        tl.addWidget(QLabel("<b>Műveletek</b>"))

        # 1. Alaphelyzet
        self.btn_reset = QPushButton(self.ls.get_button_label("alaphelyzet"))
        self.btn_reset.clicked.connect(self.reset_to_default_view)
        tl.addWidget(self.btn_reset)

        # 2. Kijelöltek letöltése
        self.btn_download_sel = QPushButton(self.ls.get_button_label("kijeloltek_letoltese"))
        self.btn_download_sel.clicked.connect(self.download_selected)
        tl.addWidget(self.btn_download_sel)

        # 3. Kijelölések törlése
        self.btn_clear_sel = QPushButton(self.ls.get_button_label("kijelolesek_torlese"))
        self.btn_clear_sel.clicked.connect(self.clear_marks)
        tl.addWidget(self.btn_clear_sel)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setFrameShadow(QFrame.Sunken)
        tl.addWidget(sep1)

        # 4. Új könyvek
        self.btn_update = QPushButton(self.ls.get_button_label("uj_konyvek"))
        self.btn_update.clicked.connect(lambda: self.start_scraper("update"))
        tl.addWidget(self.btn_update)

        # 5. Régi könyvek
        self.btn_older = QPushButton(self.ls.get_button_label("regi_konyvek"))
        self.btn_older.clicked.connect(lambda: self.start_scraper("older"))
        tl.addWidget(self.btn_older)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        tl.addWidget(sep2)

        # 6. Állj
        self.btn_stop = QPushButton(self.ls.get_button_label("allj"))
        self.btn_stop.clicked.connect(self.stop_all)
        tl.addWidget(self.btn_stop)

        # 7. Beállítások
        self.btn_settings = QPushButton(self.ls.get_button_label("beallitasok"))
        self.btn_settings.clicked.connect(self.show_settings)
        tl.addWidget(self.btn_settings)

        tl.addSpacing(12)

        # ---- Szűrés ----
        tl.addWidget(QLabel("<b>Szűrés</b>"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Keresés...")
        self.search_edit.textChanged.connect(lambda: self.refresh_data(reset_page=True))
        tl.addWidget(self.search_edit)

        tl.addWidget(QLabel("Formátum:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("Minden formátum")
        self._populate_formats()
        self.format_combo.currentTextChanged.connect(
            lambda: self.refresh_data(reset_page=True)
        )
        tl.addWidget(self.format_combo)

        self.lbl_col_filters = QLabel("")
        self.lbl_col_filters.setWordWrap(True)
        self.lbl_col_filters.setVisible(False)
        tl.addWidget(self.lbl_col_filters)
        self.btn_clear_col_filters = QPushButton("✖ Oszlopszűrők törlése")
        self.btn_clear_col_filters.setVisible(False)
        self.btn_clear_col_filters.clicked.connect(self.clear_column_filters)
        tl.addWidget(self.btn_clear_col_filters)

        tl.addStretch()

        # Műveletek/Szűrés | Kijelölt könyvek | Napló — húzható elválasztókkal
        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.addWidget(top_scroll)

        # ---- Kijelölt könyvek lista ----
        marked_box = QWidget()
        mb_lay = QVBoxLayout(marked_box)
        mb_lay.setContentsMargins(0, 0, 0, 0)
        self.marked_label = QLabel("<b>Kijelölt könyvek</b> (0)")
        mb_lay.addWidget(self.marked_label)

        self.marked_list = QListWidget()
        self.marked_list.setMinimumHeight(50)
        self.marked_list.setStyleSheet(
            "QListWidget { background: #1a2a1a; color: #a0d0a0; "
            "border: 1px solid #2d7a3a; border-radius: 4px; }"
        )
        mb_lay.addWidget(self.marked_list)
        self.left_splitter.addWidget(marked_box)

        # ---- Napló (alapból rejtett) ----
        self.log_box = log_box = QWidget()
        lb_lay = QVBoxLayout(log_box)
        lb_lay.setContentsMargins(0, 0, 0, 0)
        self.log_label = QLabel("<b>Napló</b>")
        self.log_label.setVisible(False)
        lb_lay.addWidget(self.log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setVisible(False)
        self.log_text.setMinimumHeight(50)
        self.log_text.setStyleSheet(
            "QTextEdit { background: #1a1a2e; color: #c8c8c8; "
            "font-family: Consolas, monospace; "
            "border: 1px solid #444; border-radius: 4px; }"
        )
        lb_lay.addWidget(self.log_text)
        self.left_splitter.addWidget(log_box)
        log_box.setVisible(False)

        fl.addWidget(self.left_splitter, 1)

        # Kilépés gomb - a panel legalján
        sep_exit = QFrame()
        sep_exit.setFrameShape(QFrame.HLine)
        sep_exit.setFrameShadow(QFrame.Sunken)
        fl.addWidget(sep_exit)

        self.btn_exit = QPushButton(self.ls.get_button_label("kilepes"))
        self.btn_exit.clicked.connect(self.graceful_exit)
        fl.addWidget(self.btn_exit)

        self.filter_dock.setWidget(fw)

        min_w = self.ls.get("bal_panel", "min_szelesseg", default=180)
        fw.setMinimumWidth(min_w)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.filter_dock)

        # ============ JOBB OLDALI PANEL ============
        self.details_dock = QDockWidget("Részletek", self)
        self.details_dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable
        )
        self.details_panel = DetailsPanel()
        self.details_dock.setWidget(self.details_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.details_dock)
        if not self.ls.get("jobb_panel", "lathato", default=True):
            self.details_dock.hide()

        # Kiválasztás figyelése (jobb oldali részletek panelhez)
        self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)

        # Betűméret: Ctrl+Plusz / Ctrl+Mínusz / Ctrl+0
        for keys, delta in (("Ctrl++", 1), ("Ctrl+=", 1), ("Ctrl+-", -1)):
            QShortcut(QKeySequence(keys), self, lambda d=delta: self.change_font_size(d))
        QShortcut(QKeySequence("Ctrl+0"), self,
                  lambda: self.apply_font_size(self.FONT_DEFAULT))
        self.table_font_size = self.ls.get("tablazat", "betumeret")  # None = főablaké
        if self.table_font_size:
            self.apply_table_font(self.table_font_size)
        self.apply_font_size(self.config_gui.get("font", "size", default=self.FONT_DEFAULT))

        self.statusBar().showMessage("Kész")

    # ======================== ALAPHELYZET ========================
    def reset_to_default_view(self):
        """Alaphelyzet: minden szűrés, keresés és kijelölés törlése,
        rendezés feltöltési dátum szerint csökkenően, első oldal."""
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)

        self.format_combo.blockSignals(True)
        self.format_combo.setCurrentIndex(0)
        self.format_combo.blockSignals(False)

        self.model.clear_marks()
        self.update_marked_list()
        self.column_filters.clear()
        self._update_column_filter_ui()

        self.order_by = "feltoltve_datum"
        self.desc = True
        self.current_page = 0
        self.reload_cache()
        self.refresh_from_cache()
        self.log("📋 Alaphelyzet - legfrissebb feltöltések")

    # ======================== OSZLOPOK ========================
    def load_columns_from_state(self):
        cols = self.ls.get_columns_for_model()
        if not cols:
            cols = [
                {"name": "ncore_id", "label": "Torrent ID"},
                {"name": "szerzo", "label": "Szerző"},
                {"name": "cim", "label": "Cím"},
                {"name": "sorozat", "label": "Sorozat"},
                {"name": "sorozat_szama", "label": "#"},
                {"name": "formatum", "label": "Formátum"},
                {"name": "kiadas_eve", "label": "Év"},
                {"name": "feltoltve_datum", "label": "Feltöltve"},
            ]
        self.model.columns = cols

    def apply_column_visibility(self, visibility):
        """Oszlopok ki/bekapcsolása (Beállítások → Oszlopok) azonnal."""
        # Előbb a jelenlegi szélességek mentése a régi láthatóság szerint
        self.ls.set_column_widths(
            [self.table_view.columnWidth(i) for i in range(self.model.columnCount())]
        )
        self.ls.set_columns_visibility(visibility)
        self._reload_columns()

    def _reload_columns(self):
        """Oszlopok újratöltése a layout_state-ből (szélességekkel együtt)."""
        self.model.beginResetModel()
        self.load_columns_from_state()
        self.model.endResetModel()
        for i, w in enumerate(self.ls.get_column_widths()):
            if i < self.model.columnCount():
                self.table_view.setColumnWidth(i, w)

    def _on_column_moved(self, logical, old_visual, new_visual):
        """Fejléc áthúzása után az új sorrendet a modellbe és a mentésbe
        írjuk; a fejléc vizuális sorrendje visszaáll (logikai = vizuális),
        így a szélességek, a rendezés és a szűrők indexei egyszerűek maradnak."""
        header = self.table_view.horizontalHeader()
        cols = self.model.columns
        order = [cols[header.logicalIndex(v)]["name"] for v in range(header.count())]
        widths = {c["name"]: self.table_view.columnWidth(i) for i, c in enumerate(cols)}

        def apply():
            header.blockSignals(True)
            for v in range(header.count()):          # vizuális sorrend visszaállítása
                header.moveSection(header.visualIndex(v), v)
            header.blockSignals(False)
            self.ls.reorder_columns(order, widths)
            self._reload_columns()
        QTimer.singleShot(0, apply)

    def apply_saved_sizes(self):
        widths = self.ls.get_column_widths()
        for i, w in enumerate(widths):
            if i < self.model.columnCount():
                self.table_view.setColumnWidth(i, w)
        bal_w = self.ls.get("bal_panel", "szelesseg", default=280)
        jobb_w = self.ls.get("jobb_panel", "szelesseg", default=420)
        try:
            docks, sizes = [], []
            if not self.filter_dock.isHidden():
                docks.append(self.filter_dock)
                sizes.append(bal_w)
            if not self.details_dock.isHidden():
                docks.append(self.details_dock)
                sizes.append(jobb_w)
            if docks:
                self.resizeDocks(docks, sizes, Qt.Horizontal)
        except Exception:
            pass

        for key, splitter in (
            (("jobb_panel", "borito_oszto"), self.details_panel.splitter),
            (("bal_panel", "lista_oszto"), self.left_splitter),
        ):
            sizes = self.ls.get(*key)
            if sizes and len(sizes) == splitter.count():
                splitter.setSizes(sizes)

    # ======================== ADATBETÖLTÉS ========================
    def reload_cache(self):
        query = self.search_edit.text() if hasattr(self, 'search_edit') else ""
        fmt_text = (
            self.format_combo.currentText()
            if hasattr(self, 'format_combo')
            else "Minden formátum"
        )
        formatum = None if fmt_text == "Minden formátum" else fmt_text

        if self.use_cache:
            self.full_cache = search_books(
                query=query, formatum=formatum,
                limit=0, order_by=self.order_by, desc=self.desc,
                column_filters=self.column_filters
            )
            self.total_count = len(self.full_cache)
        else:
            self.full_cache = []
            self.total_count = count_books(query=query, formatum=formatum,
                                           column_filters=self.column_filters)

    def _populate_formats(self):
        """Formátumok feltöltése - csak érvényes e-book/szöveg típusok."""
        try:
            current = self.format_combo.currentText()
            self.format_combo.blockSignals(True)
            self.format_combo.clear()
            self.format_combo.addItem("Minden formátum")
            for fmt in get_formats():
                if fmt.lower().strip() in VALID_FORMATS:
                    self.format_combo.addItem(fmt)
            idx = self.format_combo.findText(current)
            if idx >= 0:
                self.format_combo.setCurrentIndex(idx)
            self.format_combo.blockSignals(False)
        except Exception:
            pass

    def on_header_clicked(self, logical_index):
        col_name = self.model.columns[logical_index]["name"]
        if self.order_by == col_name:
            self.desc = not self.desc
        else:
            self.order_by = col_name
            self.desc = True
        self.reload_cache()
        self.current_page = 0
        self.refresh_from_cache()

    def refresh_data(self, format_filter=None, reset_page=True):
        if reset_page:
            self.current_page = 0
        try:
            self.reload_cache()
            self.refresh_from_cache()
        except Exception as e:
            import logging
            logging.error(f"refresh_data - Hiba: {e}")
            self.log(f"Hiba: {e}")

    def refresh_from_cache(self):
        if self.use_cache and self.full_cache:
            start = self.current_page * self.page_size
            end = start + self.page_size
            books = self.full_cache[start:end]
        else:
            books = search_books(
                query=self.search_edit.text(),
                formatum=(
                    None if self.format_combo.currentText() == "Minden formátum"
                    else self.format_combo.currentText()
                ),
                limit=self.page_size,
                offset=self.current_page * self.page_size,
                order_by=self.order_by,
                desc=self.desc,
                column_filters=self.column_filters
            )
        self.model.set_books(books)
        self.update_ui()

    # ======================== UI FRISSÍTÉS ========================
    def update_ui(self):
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)

        self.page_spin.blockSignals(True)
        self.slider.blockSignals(True)

        self.page_spin.setMaximum(total_pages)
        self.page_spin.setValue(self.current_page + 1)
        self.lbl_info.setText(
            f"{self.current_page+1} / {total_pages} "
            f"({self.total_count:,} könyv)".replace(",", " ")
        )

        self.slider.setMaximum(total_pages)
        self.slider.setValue(self.current_page + 1)

        self.slider.blockSignals(False)
        self.page_spin.blockSignals(False)

    def slider_preview(self, value):
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.lbl_info.setText(
            f"{value} / {total_pages} "
            f"({self.total_count:,} könyv)".replace(",", " ")
        )

    def slider_released(self):
        self.current_page = self.slider.value() - 1
        self.refresh_from_cache()

    def spin_page_changed(self, value):
        new_page = value - 1
        if new_page != self.current_page:
            self.current_page = new_page
            self.refresh_from_cache()

    # ======================== HELYI MENÜ ========================
    def show_context_menu(self, pos):
        """Helyi menü: rendezés minden oszlopban,
        keresés a cella tartalmával (ncore_id, szerző, cím, sorozat)."""
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            return

        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return

        src_index = self.proxy.mapToSource(index)
        col = self.model.columns[src_index.column()]
        col_name, col_label = col["name"], col["label"]

        menu = QMenu(self)

        # Keresőmező a cella szövegével előtöltve: szerkeszthető, Enter → keresés
        # csak ebben az oszlopban
        cell_value = (self.model.data(src_index, Qt.DisplayRole) or "").strip()
        box = QWidget()
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(8, 6, 8, 6)
        box_lay.addWidget(QLabel(f"🔍 Keresés a(z) <b>{col_label}</b> oszlopban "
                                 f"<small>(szerkeszd, majd Enter)</small>:"))
        edit = QLineEdit(cell_value)
        edit.setPlaceholderText("Írd be, majd Enter…")
        edit.setClearButtonEnabled(True)
        text_w = edit.fontMetrics().horizontalAdvance(cell_value) + 40
        edit.setMinimumWidth(max(260, min(text_w, 700)))
        edit.setCursorPosition(len(cell_value))
        box_lay.addWidget(edit)
        wa = QWidgetAction(menu)
        wa.setDefaultWidget(box)
        menu.addAction(wa)

        def apply():
            self.set_column_filter(col_name, edit.text().strip())
            menu.close()
        edit.returnPressed.connect(apply)

        if col_name in self.column_filters:
            menu.addSeparator()
            menu.addAction(
                f"✖ Szűrő törlése: {col_label} = „{self.column_filters[col_name]}”",
                lambda: self.set_column_filter(col_name, "")
            )
        if len(self.column_filters) > 1 or (
                self.column_filters and col_name not in self.column_filters):
            menu.addAction("✖ Minden oszlopszűrő törlése", self.clear_column_filters)

        QTimer.singleShot(0, edit.setFocus)
        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def show_header_menu(self, pos):
        """Oszlopfejlécre jobb klikk: rendezés (és az oszlop szűrőjének törlése)."""
        header = self.table_view.horizontalHeader()
        section = header.logicalIndexAt(pos)
        if section < 0 or section >= len(self.model.columns):
            return
        col = self.model.columns[section]
        col_name, col_label = col["name"], col["label"]

        menu = QMenu(self)
        menu.addAction(f"↑ Rendezés: {col_label} – növekvő",
                       lambda: self._sort_column(col_name, False))
        menu.addAction(f"↓ Rendezés: {col_label} – csökkenő",
                       lambda: self._sort_column(col_name, True))
        if col_name in self.column_filters:
            menu.addSeparator()
            menu.addAction(f"✖ Szűrő törlése: „{self.column_filters[col_name]}”",
                           lambda: self.set_column_filter(col_name, ""))
        menu.exec(header.mapToGlobal(pos))

    # ---- Oszloponkénti szűrők ----
    def set_column_filter(self, col_name: str, text: str):
        if text:
            self.column_filters[col_name] = text
        else:
            self.column_filters.pop(col_name, None)
        self._update_column_filter_ui()
        self.refresh_data(reset_page=True)

    def clear_column_filters(self):
        self.column_filters.clear()
        self._update_column_filter_ui()
        self.refresh_data(reset_page=True)

    def _update_column_filter_ui(self):
        labels = {c["nev"]: c["cimke"] for c in self.ls.get_all_columns()}
        self.model.filtered_columns = set(self.column_filters)
        self.model.headerDataChanged.emit(
            Qt.Horizontal, 0, max(0, self.model.columnCount() - 1))
        if self.column_filters:
            parts = [f"{labels.get(c, c)}: „{t}”" for c, t in self.column_filters.items()]
            self.lbl_col_filters.setText("<b>Oszlopszűrők:</b><br>" + "<br>".join(parts))
        self.lbl_col_filters.setVisible(bool(self.column_filters))
        self.btn_clear_col_filters.setVisible(bool(self.column_filters))

    def _sort_column(self, col_name: str, descending: bool):
        """Rendezés a megadott oszlop szerint."""
        self.order_by = col_name
        self.desc = descending
        self.reload_cache()
        self.current_page = 0
        self.refresh_from_cache()

    def _search_from_context(self, value: str):
        """Keresés a helyi menüből - halmozódó szűrés.

        Az új kifejezés hozzáfűződik a meglévő kereséshez,
        így a szűrés egyre szűkül. Az Alaphelyzet gomb törli az összeset.
        """
        current = self.search_edit.text().strip()
        if current:
            if value.lower() in current.lower():
                return
            new_text = f"{current} {value}"
        else:
            new_text = value
        self.search_edit.setText(new_text)

    # ======================== LAPOZÁS ========================
    def first_page(self):
        self.current_page = 0
        self.refresh_from_cache()

    def prev_page(self):
        self.current_page = max(0, self.current_page - 1)
        self.refresh_from_cache()

    def next_page(self):
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.current_page = min(self.current_page + 1, total_pages - 1)
        self.refresh_from_cache()

    def last_page(self):
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.current_page = total_pages - 1
        self.refresh_from_cache()

    def change_page_size(self):
        self.page_size = int(self.page_size_combo.currentText())
        self.current_page = 0
        self.refresh_data(reset_page=True)

    # ======================== SCRAPER ========================
    def start_scraper(self, mode: str):
        """Scraper indítása háttérszálban."""
        if self.worker and self.worker.isRunning():
            self.log("⏳ A scraper még fut, várd meg a befejezését!")
            return

        cfg = config.load_config()
        if not cfg.get("username") or not cfg.get("password"):
            QMessageBox.warning(
                self, "Hiányzó bejelentkezési adatok",
                "Nincs megadva felhasználónév vagy jelszó!\n"
                "Add meg a Beállítások menüben."
            )
            self.show_settings()
            return

        self.worker = ScraperWorker(mode)
        self.worker.finished.connect(self.on_scraper_finished)
        self.worker.log_signal.connect(self.log)
        self.worker.start()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_update.setEnabled(False)
        self.btn_older.setEnabled(False)
        self._show_log_panel(True)
        self.log_text.clear()
        mode_name = "Új könyvek keresése" if mode == "update" else "Régi könyvek keresése"
        self.log(f"▶ {mode_name} indul...")

    def on_scraper_finished(self, count):
        self.progress_bar.setVisible(False)
        self.btn_update.setEnabled(True)
        self.btn_older.setEnabled(True)

        if count == -1:
            QMessageBox.information(
                self, "Üres adatbázis",
                "Az adatbázis üres!\n\n"
                "Először az 'Új könyvek' gombbal tölts le adatokat."
            )
        elif count == 0 and self.worker and self.worker.mode == "older":
            QMessageBox.information(
                self, "Minden megvan",
                "Nincs mit letölteni - a legkorábbi torrent adatai\n"
                "is szerepelnek már az adatbázisban."
            )
        else:
            self.log(f"✅ Kész! {count} könyv mentve.")

        self._populate_formats()
        self.refresh_data(reset_page=True)

    # ======================== MEGJELÖLÉS / KIVÁLASZTÁS ========================
    def on_selection_changed(self):
        """A tábla kiválasztás változásakor frissítjük a jobb oldali részleteket."""
        idx = self.table_view.selectionModel().selectedRows()
        if idx:
            src = self.proxy.mapToSource(idx[0])
            if src.row() < len(self.model.books):
                book = self.model.books[src.row()]
                self.details_panel.update_info(book)

    def on_double_click(self, index):
        """Dupla kattintás: megjelölés ki/be váltása."""
        src_index = self.proxy.mapToSource(index)
        self.model.toggle_mark(src_index.row())
        self.update_marked_list()

    def clear_marks(self):
        """Minden megjelölés törlése."""
        self.model.clear_marks()
        self.update_marked_list()
        self.log("Kijelölések törölve.")

    def update_marked_list(self):
        """A bal panelen lévő kijelölt könyvek lista frissítése."""
        self.marked_list.clear()
        count = len(self.model.marked_ids)
        self.marked_label.setText(f"<b>Kijelölt könyvek</b> ({count})")

        if count == 0:
            return

        # Az aktuális oldalon lévő megjelölt könyvek adatait jelenítjük meg
        for book in self.model.books:
            nid = str(book.get("ncore_id", ""))
            if nid in self.model.marked_ids:
                szerzo = book.get("szerzo", "?")
                cim = book.get("cim", "?")
                item = QListWidgetItem(f"{szerzo} - {cim}")
                self.marked_list.addItem(item)

        # Ha vannak más oldalon megjelöltek is, jelezzük
        on_page = sum(
            1 for b in self.model.books
            if str(b.get("ncore_id", "")) in self.model.marked_ids
        )
        if count > on_page:
            item = QListWidgetItem(f"... +{count - on_page} másik oldalon")
            item.setForeground(QBrush(QColor("#888")))
            self.marked_list.addItem(item)

    def download_selected(self):
        """A megjelölt (zöld) könyvek letöltése."""
        marked = self.model.marked_ids
        if not marked:
            QMessageBox.information(self, "Nincs kijelölés",
                                    "Jelölj ki legalább egy könyvet!\n\n"
                                    "Dupla kattintással vagy Ctrl+kattintással jelölhetsz.")
            return

        ncore_ids = list(marked)
        if not self.downloader.connect():
            QMessageBox.warning(self, "Hiba", "A bejelentkezés sikertelen!")
            return
        self._show_log_panel(True)
        self.log_text.clear()
        folder = self.downloader.download_path
        self.log(f"📥 {len(ncore_ids)} torrent letöltése indul...")
        self.log(f"📁 Mappa: {folder}")
        ok = 0
        for nid in ncore_ids:
            if self.downloader.download_by_ncore_id(nid):
                ok += 1
                name = os.path.basename(self.downloader.last_file or nid)
                self.log(f"✅ {name} ({ok}/{len(ncore_ids)})")
            else:
                self.log(f"❌ {nid} sikertelen")
            QApplication.processEvents()
        self.log(f"📥 Letöltés kész: {ok}/{len(ncore_ids)} sikeres")
        self.log(f"📁 Mentve ide: {folder}")
        if ok:
            reply = QMessageBox.question(
                self, "Letöltés kész",
                f"{ok} .torrent fájl mentve ide:\n\n{folder}\n\n"
                "Megnyitod a mappát?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    # ======================== ÁLLJ / KILÉPÉS ========================
    def stop_all(self):
        """Minden futó művelet leállítása."""
        stopped = False
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.quit()
            self.worker.wait(3000)
            self.progress_bar.setVisible(False)
            self.btn_update.setEnabled(True)
            self.btn_older.setEnabled(True)
            stopped = True

        if stopped:
            self.log("🛑 Minden művelet leállítva.")
        else:
            self.log("Nincs futó művelet.")

    def graceful_exit(self):
        """Leállít mindent, menti az állapotot, majd bezárja az alkalmazást."""
        self.stop_all()
        self.save_current_state()
        QApplication.quit()

    # ======================== BEÁLLÍTÁSOK ========================
    def _show_log_panel(self, visible: bool):
        """Napló panel megjelenítése vagy elrejtése."""
        if hasattr(self, 'log_text'):
            self.log_box.setVisible(visible)
            self.log_label.setVisible(visible)
            self.log_text.setVisible(visible)

    # ======================== BETŰMÉRET ========================
    FONT_MIN, FONT_MAX, FONT_DEFAULT = 7, 28, 10

    def apply_font_size(self, size: int):
        """Betűméret beállítása az egész ablakra (és mentése)."""
        size = max(self.FONT_MIN, min(self.FONT_MAX, int(size)))
        self.config_gui.set("font", "size", size)
        self.config_gui.save()
        self.setStyleSheet(self.config_gui.generate_stylesheet())

        self._update_table_row_height()
        self.statusBar().showMessage(f"Betűméret: {size} pt", 3000)

    def _update_table_row_height(self):
        """Táblázat sormagassága igazodjon a (táblázat vagy főablak) betűhöz."""
        size = self.table_font_size or self.config_gui.get(
            "font", "size", default=self.FONT_DEFAULT)
        family = self.config_gui.get("font", "family", default="Segoe UI")
        fm = QFontMetrics(QFont(family, size))
        self.table_view.verticalHeader().setDefaultSectionSize(fm.height() + 10)
        self.lbl_table_font.setText(f"{size} pt")

    def apply_table_font(self, size: int):
        """A középső táblázat saját betűmérete (a főablaktól függetlenül)."""
        size = max(self.FONT_MIN, min(self.FONT_MAX, int(size)))
        self.table_font_size = size
        self.table_view.setStyleSheet(f"* {{ font-size: {size}pt; }}")
        self.ls.set("tablazat", "betumeret", size)
        self._update_table_row_height()

    def change_table_font(self, delta: int):
        current = self.table_font_size or self.config_gui.get(
            "font", "size", default=self.FONT_DEFAULT)
        self.apply_table_font(current + delta)

    def change_font_size(self, delta: int):
        current = self.config_gui.get("font", "size", default=self.FONT_DEFAULT)
        self.apply_font_size(current + delta)

    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.use_cache = self.ls.get("altalanos", "cache_hasznalat", default=True)
            self.refresh_data(reset_page=True)

    # ======================== ÁLLAPOT MENTÉS ========================
    def save_current_state(self):
        geo = self.geometry()
        self.ls.set("foablak", "szelesseg", geo.width())
        self.ls.set("foablak", "magassag", geo.height())
        self.ls.set("foablak", "x_pozicio", geo.x())
        self.ls.set("foablak", "y_pozicio", geo.y())
        self.ls.set("foablak", "maximalizalt", self.isMaximized())

        self.ls.set("bal_panel", "lathato", not self.filter_dock.isHidden())
        self.ls.set("bal_panel", "szelesseg", self.filter_dock.width())

        self.ls.set("jobb_panel", "lathato", not self.details_dock.isHidden())
        self.ls.set("jobb_panel", "szelesseg", self.details_dock.width())
        self.ls.set("jobb_panel", "borito_oszto", self.details_panel.splitter.sizes())
        self.ls.set("bal_panel", "lista_oszto", self.left_splitter.sizes())

        widths = [
            self.table_view.columnWidth(i)
            for i in range(self.model.columnCount())
        ]
        self.ls.set_column_widths(widths)

        self.ls.set("lapozas", "oldalmeret", self.page_size)
        self.ls.set("altalanos", "rendezes_oszlop", self.order_by)
        self.ls.set("altalanos", "rendezes_csokkeno", self.desc)
        self.ls.set("altalanos", "cache_hasznalat", self.use_cache)

        self.ls.save()

    def closeEvent(self, event):
        # Kilépéskor megvárjuk, hogy a scraper befejezze az aktuális oldalt
        # (lekérés + borító + késleltetés akár 30 mp), különben a szál
        # félbeszakad ("QThread: Destroyed while thread is still running").
        if self.worker and self.worker.isRunning():
            self.statusBar().showMessage("⏳ Scraper leállítása, kis türelmet...")
            QApplication.processEvents()
            self.worker.stop()
            self.worker.wait(30000)
        self.stop_all()
        self.save_current_state()
        event.accept()


# ====================== INDÍTÁS ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
