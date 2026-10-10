# nCore eBook Manager – refaktorálási csomag

A `nCore_Scraper.exe` forrása (PySide6 asztali alkalmazás). GitHub: https://github.com/sanyi1963bp/Ncore-manager-

## Indítás

```
pip install PySide6 requests beautifulsoup4
copy config.minta.json config.json      (felhasználónév/jelszó a Beállításokban is megadható)
copy minta_adatbazis.db ncore_konyvtar.db
python run_ncore.py
```

Az `ncore_konyvtar.db` és a `config.json` nincs a csomagban. A `minta_adatbazis.db` a valódi
adatbázis szerkezete 200 könyvvel, az `adatbazis_sema.sql` a teljes séma (a valódi adatbázisban
kb. 68 700 könyv van).

## Modulok

| Fájl | Szerep |
|---|---|
| `run_ncore.py` | Belépési pont (PyInstaller is ezt fordítja) |
| `Main_window.py` | A teljes GUI (~1800 sor): táblázat-modell, `BookTableView` (jelölés), `ScraperWorker` (QThread), `SettingsDialog`, `CoverLabel`, `DetailsPanel`, `MainWindow` |
| `database.py` | SQLite-hozzáférés (`search_books`, `count_books`, mentés/visszaállítás a `backups/` mappába) |
| `scraper.py` | nCore bejelentkezés + lista/adatlap scraping (requests + BeautifulSoup), borítóletöltés |
| `downloader.py` | `.torrent` fájlok letöltése a figyelt mappába |
| `config.py` | `config.json` (belépési adatok, útvonalak) |
| `gui_config.py` | Témák, stíluslap generálás, főablak-betűméret (`gui_config.json`) |
| `layout_state.py` | Ablak/panel/oszlop állapot (`layout_state.json`, `layout_default.json`) |
| `build_ncore.bat` | EXE készítés PyInstallerrel (`dist\nCore_Scraper\`) |
| `Inditas.bat` | Indítás forrásból Python 3.12-vel |

## Refaktorálásnál érdemes tudni

- **`Main_window.py` túl nagy**: minden GUI-osztály egy fájlban. Kézenfekvő bontás:
  `table_model.py`, `table_view.py`, `details_panel.py`, `settings_dialog.py`, `scraper_worker.py`, `main_window.py`.
- **Két konfigurációs rendszer** van párhuzamosan (`gui_config.json` és `layout_state.json`), átfedéssel
  (pl. ablakméret, panelek). Összevonható.
- **Betűméretek**: főablak → `gui_config.json` `font.size`; táblázat → `layout_state.json` `tablazat.betumeret`;
  jobb panel → `layout_state.json` `jobb_panel.betumeret`. A `gui_config.json` `font.table_size` mezője nincs használva.
- **Jelölés** (`BookTableModel.marked_ids`, ncore_id-k halmaza): Ctrl+klikk, egérhúzás, Shift+nyilak/Home/End/PgUp/PgDn;
  levétel: Ctrl+jobb klikk, jobb gombos húzás, Shift+jobb klikk. A logika a `BookTableView`-ban van.
- **A jelszó szabad szövegként van a `config.json`-ban.** Jobb lenne a Windows Credential Manager (`keyring` csomag).
- **`build_ncore.bat`** az exe készítésekor a forrásmappa adatbázisát másolja a `dist` mappába,
  ami felülírhatja az exe mellett lévő, élő adatbázist.
- **Kilépés**: a `closeEvent` legfeljebb 30 mp-ig várja a futó scrapert (`scraper.stop_requested` jelző).
- **Relatív útvonalak**: a program a munkakönyvtárhoz képest keresi a `config.json`-t, a `boritok/`-at és a `*.db`-t
  (exe-ként a `run_ncore.py` az exe mappájába lép).
- Tesztek nincsenek. A GUI ablak nélkül is tesztelhető: `QT_QPA_PLATFORM=offscreen`.
