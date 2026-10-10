# nCore Scraper – refaktorált változat

Ez a változat az eredeti projekt működését igyekszik változatlanul megőrizni, miközben a nagy GUI és scraper modulokat külön fájlokra bontja.

## Indítás

Windows alatt futtasd a `Inditas.bat` fájlt, vagy:

```text
python run_ncore.py
```

## Főbb modulok

- `main_window.py` – főablak
- `ui/` – GUI komponensek
- `core/ncore_session.py` – nCore HTTP session és bejelentkezés
- `core/scraper.py` – scraping logika
- `scraper.py` és `Main_window.py` – kompatibilitási átjárók

Az eredeti projekt külön példányát nem módosítottuk.
