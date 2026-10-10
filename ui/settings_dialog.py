from .common import *

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Beállítások")
        self.setMinimumSize(550, 550)
        self.config_gui = gui_config.get_config()
        self.layout_state = get_layout_state()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # ---- Fiók fül ----
        gen_tab = QWidget()
        gen_lay = QFormLayout(gen_tab)
        curr = config.load_config()

        self.user_edit = QLineEdit(curr.get("username", ""))
        gen_lay.addRow("Felhasználónév:", self.user_edit)

        self.pass_edit = QLineEdit(curr.get("password", ""))
        self.pass_edit.setEchoMode(QLineEdit.Password)
        gen_lay.addRow("Jelszó:", self.pass_edit)

        self.path_edit = QLineEdit(curr.get("torrent_watch_folder", ""))
        gen_lay.addRow("Torrent mappa:", self.path_edit)

        tabs.addTab(gen_tab, "Fiók")

        # ---- Megjelenés fül ----
        app_tab = QWidget()
        app_lay = QVBoxLayout(app_tab)
        self.theme_combo = QComboBox()
        for key, theme in gui_config.THEMES.items():
            self.theme_combo.addItem(theme['name'], key)
        self.theme_combo.setCurrentText(
            gui_config.THEMES[self.config_gui.get("theme", default="midnight")]["name"]
        )
        app_lay.addWidget(QLabel("Színséma:"))
        app_lay.addWidget(self.theme_combo)

        app_lay.addSpacing(12)
        app_lay.addWidget(QLabel("Betűméret (pt) — gyorsbillentyű: Ctrl+Plusz / Ctrl+Mínusz / Ctrl+0:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(FONT_MIN, FONT_MAX)
        self.font_spin.setValue(self.config_gui.get("font", "size", default=FONT_DEFAULT))
        app_lay.addWidget(self.font_spin)

        app_lay.addSpacing(20)
        self.cb_cache = QCheckBox("Memória-cache használata rendezéshez")
        self.cb_cache.setChecked(
            self.layout_state.get("altalanos", "cache_hasznalat", default=True)
        )
        app_lay.addWidget(self.cb_cache)

        app_lay.addSpacing(20)
        app_lay.addWidget(QLabel("<b>Panelek:</b>"))
        self.cb_details = QCheckBox("Jobb oldali részletek panel")
        self.cb_details.setChecked(not self.parent().details_dock.isHidden())
        app_lay.addWidget(self.cb_details)
        app_lay.addStretch()
        tabs.addTab(app_tab, "Megjelenés")

        # ---- Oszlopok fül ----
        col_tab = QWidget()
        col_lay = QVBoxLayout(col_tab)
        col_lay.addWidget(QLabel(
            "<b>Táblázat oszlopai</b><br>"
            "Jelöld be, mely oszlopok látszódjanak a középső táblázatban."
        ))
        col_lay.addSpacing(8)
        self.col_checks = {}
        for c in self.layout_state.get_all_columns():
            cb = QCheckBox(c["cimke"])
            cb.setChecked(c.get("lathato", True))
            self.col_checks[c["nev"]] = cb
            col_lay.addWidget(cb)
        col_lay.addSpacing(8)
        col_btns = QHBoxLayout()
        btn_all = QPushButton("Mind")
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self.col_checks.values()])
        col_btns.addWidget(btn_all)
        col_btns.addStretch()
        col_lay.addLayout(col_btns)
        col_lay.addStretch()
        tabs.addTab(col_tab, "Oszlopok")

        # ---- Elrendezés fül ----
        layout_tab = QWidget()
        lt_lay = QVBoxLayout(layout_tab)
        lt_lay.addWidget(QLabel(
            "<b>Elrendezés kezelése</b><br><br>"
            "Az ablak bezárásakor az összes méret és pozíció<br>"
            "automatikusan mentődik a <i>layout_state.json</i> fájlba.<br><br>"
            "Az aktuális állapotot itt mentheted el alapértelmezettként,<br>"
            "illetve itt állíthatod vissza a korábban mentett alapértelmezést."
        ))
        lt_lay.addSpacing(20)

        btn_save_def = QPushButton("💾 Jelenlegi állapot mentése alapértelmezettként")
        btn_save_def.clicked.connect(self._save_layout_default)
        lt_lay.addWidget(btn_save_def)

        lt_lay.addSpacing(10)
        btn_restore_def = QPushButton("🔄 Alapértelmezett elrendezés visszaállítása")
        btn_restore_def.clicked.connect(self._restore_layout_default)
        lt_lay.addWidget(btn_restore_def)

        lt_lay.addStretch()
        tabs.addTab(layout_tab, "Elrendezés")

        # ---- Adatbázis fül ----
        db_tab = QWidget()
        db_lay = QVBoxLayout(db_tab)
        db_lay.addWidget(QLabel(
            "<b>Biztonsági mentés és visszaállítás</b><br><br>"
            "Az adatbázisról bármikor készíthetsz biztonsági másolatot.<br>"
            "Visszaállításkor az aktuális állapotról automatikusan<br>"
            "mentés készül, mielőtt felülíródna."
        ))
        db_lay.addSpacing(10)

        btn_backup = QPushButton("💾 Biztonsági mentés készítése")
        btn_backup.clicked.connect(self._create_backup)
        db_lay.addWidget(btn_backup)

        db_lay.addSpacing(16)
        db_lay.addWidget(QLabel("<b>Elérhető mentések:</b>"))

        self.backup_list = QListWidget()
        self.backup_list.setMinimumHeight(150)
        self.backup_list.setStyleSheet(
            "QListWidget { font-family: Consolas, monospace; font-size: 12px; }"
        )
        db_lay.addWidget(self.backup_list, 1)

        btn_row = QHBoxLayout()
        btn_restore = QPushButton("🔄 Visszaállítás a kijelöltből")
        btn_restore.clicked.connect(self._restore_backup)
        btn_row.addWidget(btn_restore)

        btn_del = QPushButton("🗑 Kijelölt mentés törlése")
        btn_del.clicked.connect(self._delete_backup)
        btn_row.addWidget(btn_del)
        db_lay.addLayout(btn_row)

        db_lay.addStretch()
        tabs.addTab(db_tab, "Adatbázis")

        self._refresh_backup_list()

        layout.addWidget(tabs)
        save_btn = QPushButton("💾 Mentés és alkalmazás")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _save(self):
        username = self.user_edit.text().strip()
        password = self.pass_edit.text().strip()

        if not username or not password:
            QMessageBox.warning(
                self, "Hiányzó adatok",
                "A felhasználónév és a jelszó megadása kötelező!\n"
                "Ezek nélkül a scraper és a letöltés nem működik."
            )
            return

        if not any(cb.isChecked() for cb in self.col_checks.values()):
            QMessageBox.warning(
                self, "Nincs oszlop",
                "Legalább egy oszlopot jelölj be a táblázathoz!"
            )
            return

        config.set("username", username)
        config.set("password", password)
        config.set("torrent_watch_folder", self.path_edit.text().strip())

        self.parent().details_dock.setVisible(self.cb_details.isChecked())
        self.config_gui.set("theme", self.theme_combo.currentData())
        self.config_gui.save()
        self.layout_state.set("altalanos", "cache_hasznalat", self.cb_cache.isChecked())
        self.parent().apply_column_visibility(
            {name: cb.isChecked() for name, cb in self.col_checks.items()}
        )
        self.layout_state.save()
        self.parent().apply_font_size(self.font_spin.value())  # stíluslapot is újragenerálja
        self.accept()

    def _save_layout_default(self):
        self.parent().save_current_state()
        self.layout_state.save_as_default()
        QMessageBox.information(
            self, "Elrendezés",
            "A jelenlegi elrendezés elmentve alapértelmezettként!\n\n"
            "Ezt bármikor visszaállíthatod a másik gombbal."
        )

    def _restore_layout_default(self):
        reply = QMessageBox.question(
            self, "Visszaállítás",
            "Biztosan visszaállítod az alapértelmezett elrendezést?\n\n"
            "A változás az újraindítás után lép érvénybe.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.layout_state.restore_default()
            QMessageBox.information(
                self, "Kész",
                "Az alapértelmezés visszaállítva!\n"
                "Indítsd újra az alkalmazást az érvénybe lépéshez."
            )
            self.accept()

    # ---- Adatbázis mentés ----

    def _refresh_backup_list(self):
        """Mentések listájának frissítése."""
        self.backup_list.clear()
        for b in list_backups():
            item = QListWidgetItem(
                f"{b['date']}   ({b['size_mb']:.1f} MB)   {b['name']}"
            )
            item.setData(Qt.UserRole, b["path"])
            self.backup_list.addItem(item)
        if self.backup_list.count() == 0:
            item = QListWidgetItem("  (nincs mentés)")
            item.setFlags(Qt.NoItemFlags)
            self.backup_list.addItem(item)

    def _create_backup(self):
        """Biztonsági mentés készítése."""
        result = create_backup()
        if result:
            QMessageBox.information(
                self, "Mentés kész",
                f"Biztonsági mentés sikeresen elkészült!\n\n{result}"
            )
            self._refresh_backup_list()
        else:
            QMessageBox.warning(
                self, "Hiba",
                "A biztonsági mentés nem sikerült!"
            )

    def _restore_backup(self):
        """Visszaállítás a kijelölt mentésből."""
        item = self.backup_list.currentItem()
        if not item or not item.data(Qt.UserRole):
            QMessageBox.information(self, "Nincs kijelölés",
                                    "Válassz ki egy mentést a listából!")
            return

        path = item.data(Qt.UserRole)
        name = item.text().strip()

        reply = QMessageBox.question(
            self, "Visszaállítás megerősítése",
            f"Biztosan visszaállítod az adatbázist?\n\n"
            f"Mentés: {name}\n\n"
            f"Az aktuális adatbázisról automatikusan\n"
            f"biztonsági másolat készül a visszaállítás előtt.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if restore_backup(path):
            QMessageBox.information(
                self, "Visszaállítás kész",
                "Az adatbázis sikeresen visszaállítva!\n\n"
                "Az alkalmazást újra kell indítani\n"
                "a változások érvénybe lépéséhez."
            )
            self._refresh_backup_list()
        else:
            QMessageBox.warning(self, "Hiba",
                                "A visszaállítás nem sikerült!")

    def _delete_backup(self):
        """Kijelölt mentés törlése."""
        item = self.backup_list.currentItem()
        if not item or not item.data(Qt.UserRole):
            QMessageBox.information(self, "Nincs kijelölés",
                                    "Válassz ki egy mentést a listából!")
            return

        path = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Törlés megerősítése",
            f"Biztosan törlöd ezt a mentést?\n\n{item.text().strip()}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if delete_backup(path):
                self._refresh_backup_list()
            else:
                QMessageBox.warning(self, "Hiba",
                                    "A mentés törlése nem sikerült!")


# nCore torrent oldal URL sablon
NCORE_DETAIL_URL = "https://ncore.pro/torrents.php?action=details&id={ncore_id}"
# Moly.hu keresés URL sablon (magyar könyvkatalógus, ismertetők, vásárlás)
MOLY_SEARCH_URL = "https://moly.hu/kereses?utf8=%E2%9C%93&q={query}"


# ====================== BORÍTÓ ======================
