"""Schema migration v1 -> v2: add OCR provenance to entries.

Adds two columns to `entries` so Phase 2 can track which OCR pass each
entry was parsed from. Lets the orchestrator detect when a page's OCR
upgrades from Tesseract to Claude-vision after the entry was parsed,
and re-dispatch parsing for that page (Plan C reparse-on-upgrade).

Per spec §9, schema_version is bumped in `meta` and a migration note is
recorded. Re-running this script is a no-op (idempotent).
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

TARGET_VERSION = "2"
MIGRATION_NOTE = (
    "added source_ocr_agent + source_ocr_at to entries for Plan C "
    "reparse-on-OCR-upgrade hook"
)


def column_exists(con: sqlite3.Connection, table: str, column: str) -> bool:
    return any(r[1] == column for r in con.execute(f"PRAGMA table_info({table})"))


def main() -> int:
    if not DB_PATH.exists():
        print(f"missing {DB_PATH}", file=sys.stderr)
        return 1

    con = sqlite3.connect(DB_PATH)
    try:
        current = con.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        current_version = current[0] if current else "0"
        print(f"current schema_version: {current_version}")
        if current_version == TARGET_VERSION:
            # Still verify columns; tolerate prior partial migration.
            if column_exists(con, "entries", "source_ocr_agent") and column_exists(
                con, "entries", "source_ocr_at"
            ):
                print("already at v2 — no-op")
                return 0
            print("schema_version says v2 but columns missing — applying")

        with con:
            if not column_exists(con, "entries", "source_ocr_agent"):
                con.execute("ALTER TABLE entries ADD COLUMN source_ocr_agent TEXT")
                print("  + entries.source_ocr_agent")
            if not column_exists(con, "entries", "source_ocr_at"):
                con.execute("ALTER TABLE entries ADD COLUMN source_ocr_at TIMESTAMP")
                print("  + entries.source_ocr_at")
            con.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
                (TARGET_VERSION,),
            )
            now = datetime.now(timezone.utc).isoformat()
            con.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (f"migration_v{TARGET_VERSION}_at", now),
            )
            con.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (f"migration_v{TARGET_VERSION}_note", MIGRATION_NOTE),
            )
        print(f"schema_version -> {TARGET_VERSION}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
