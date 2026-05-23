"""Initialize state/run.sqlite with the Phase 0 schema (§4.4 of the spec)."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
    page_no    INTEGER PRIMARY KEY,
    png_path   TEXT NOT NULL,
    ocr_text   TEXT,
    ocr_status TEXT CHECK(ocr_status IN ('pending','done','failed')) DEFAULT 'pending',
    ocr_agent  TEXT,
    ocr_at     TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entries (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    page_no           INTEGER REFERENCES pages(page_no),
    position_on_page  INTEGER,
    lemma_greek       TEXT NOT NULL,
    lemma_translit    TEXT,
    strongs           TEXT,
    body_markdown     TEXT NOT NULL,
    papyri_citations  TEXT,
    nt_references     TEXT,
    has_translation   INTEGER DEFAULT 0,
    producer_agent    TEXT NOT NULL,
    produced_at       TIMESTAMP,
    confidence        REAL,
    needs_review      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id        INTEGER REFERENCES entries(id),
    reviewer_agent  TEXT NOT NULL,
    verdict         TEXT CHECK(verdict IN ('agree','minor','major','reject')),
    diff            TEXT,
    reviewer_lemma  TEXT,
    reviewer_strongs TEXT,
    notes           TEXT,
    reviewed_at     TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disagreements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id        INTEGER REFERENCES entries(id),
    field           TEXT,
    producer_value  TEXT,
    reviewer_value  TEXT,
    resolution      TEXT,
    resolution_by   TEXT,
    resolved_at     TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_entries_strongs ON entries(strongs);
CREATE INDEX IF NOT EXISTS idx_entries_lemma   ON entries(lemma_greek);
CREATE INDEX IF NOT EXISTS idx_reviews_entry   ON reviews(entry_id);
"""


def main() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    fresh = not DB_PATH.exists()
    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript(SCHEMA)
        con.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("schema_version", "1"),
        )
        con.commit()
    finally:
        con.close()
    print(f"{'Created' if fresh else 'Updated'} {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
