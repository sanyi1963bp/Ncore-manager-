-- ncore_konyvtar.db séma (adatok nélkül)

CREATE TABLE felhasznalo_adatok (
                konyv_id        INTEGER PRIMARY KEY,
                statusz         TEXT,
                sajat_ertekeles INTEGER,
                megjegyzes      TEXT,
                letrehozva      TEXT,
                modositva       TEXT, olvasas_kezdete TEXT, olvasas_vege TEXT, aktualis_oldal INTEGER, osszes_oldal INTEGER,
                FOREIGN KEY (konyv_id) REFERENCES konyvek(id)
            );

CREATE TABLE fizikai_fajlok (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fajl_utvonal    TEXT UNIQUE NOT NULL,
            fajl_nev        TEXT,
            formatum        TEXT,
            konyv_id        INTEGER,
            talalat_szerzo  TEXT,
            talalat_cim     TEXT,
            egyezes_szint   TEXT,
            minta           TEXT,
            szerzo_szazalek REAL DEFAULT 0,
            cim_szazalek    REAL DEFAULT 0,
            letrehozva      TIMESTAMP DEFAULT CURRENT_TIMESTAMP, moly_id TEXT,
            FOREIGN KEY (konyv_id) REFERENCES konyvek(id)
        );

CREATE TABLE konyvek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ncore_id TEXT UNIQUE NOT NULL,
    szerzo TEXT,
    cim TEXT,
    kep_utvonal TEXT,
    meret TEXT,
    feltoltve_datum TEXT,
    cimkek TEXT,
    leiras TEXT,
    buy_link TEXT,
    teljes_link TEXT,
    formatum TEXT,
    kiado TEXT,
    kiadas_eve TEXT,
    isbn TEXT,
    sorozat TEXT,
    sorozat_szama TEXT,
    letrehozva TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE moly_adatok (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            moly_id        TEXT UNIQUE,
            moly_url       TEXT,
            moly_slug      TEXT,
            szerzo         TEXT,
            cim            TEXT,
            ertekeles      TEXT,
            sorozat        TEXT,
            konyv_id       INTEGER,
            letrehozva     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (konyv_id) REFERENCES konyvek(id)
        );

CREATE TABLE moly_kereses_naplo (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            kereses    TEXT UNIQUE,
            db         INTEGER,
            letrehozva TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE sqlite_sequence(name,seq);

CREATE INDEX idx_cim ON konyvek(cim);

CREATE INDEX idx_feltoltve ON konyvek(feltoltve_datum DESC);

CREATE INDEX idx_ff_konyv ON fizikai_fajlok(konyv_id);

CREATE INDEX idx_ff_minta ON fizikai_fajlok(minta);

CREATE INDEX idx_ff_szint ON fizikai_fajlok(egyezes_szint);

CREATE INDEX idx_formatum ON konyvek(formatum);

CREATE INDEX idx_isbn ON konyvek(isbn);

CREATE INDEX idx_moly_konyv ON moly_adatok(konyv_id);

CREATE INDEX idx_moly_szerzo ON moly_adatok(szerzo);

CREATE INDEX idx_szerzo ON konyvek(szerzo);

-- konyvek: 68741 sor

-- fizikai_fajlok: 51055 sor

-- moly_adatok: 18211 sor

-- moly_kereses_naplo: 2752 sor

-- felhasznalo_adatok: 2 sor
