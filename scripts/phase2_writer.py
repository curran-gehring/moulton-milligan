"""Phase 2 writer: ingest parser JSON outputs into the `entries` table.

Each input file is a JSON array of entry objects for one page (the format
the Entry-Parser sub-agent emits per scripts/phase2_prompts.py).

The page_no is taken from the filename `tmp/parse/page-NNN.json`. The
source_ocr_agent + source_ocr_at are looked up from the `pages` table at
ingest time (snapshot of which OCR pass the parser worked from).

Idempotent: if entries already exist for the page, they are deleted along
with their reviews and disagreements before the new entries are inserted.
This is the reparse-on-OCR-upgrade hook in action.

Usage:
  python scripts/phase2_writer.py tmp/parse/page-001.json [tmp/parse/page-002.json ...]
  python scripts/phase2_writer.py --batch tmp/parse/
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

PAGE_RE = re.compile(r"page-(\d+)\.json$", re.IGNORECASE)


def page_no_from_filename(p: Path) -> int | None:
    m = PAGE_RE.search(p.name)
    return int(m.group(1)) if m else None


def ingest_page(con: sqlite3.Connection, page_no: int, entries: list[dict]) -> tuple[int, int]:
    """Returns (deleted_count, inserted_count)."""
    page_row = con.execute(
        "SELECT ocr_agent, ocr_at FROM pages WHERE page_no=?", (page_no,)
    ).fetchone()
    if not page_row:
        raise RuntimeError(f"no pages row for page_no={page_no}")
    source_ocr_agent, source_ocr_at = page_row

    # Idempotency: drop prior entries (cascade reviews + disagreements manually)
    deleted = con.execute(
        "SELECT COUNT(*) FROM entries WHERE page_no=?", (page_no,)
    ).fetchone()[0]
    con.execute(
        "DELETE FROM disagreements WHERE entry_id IN (SELECT id FROM entries WHERE page_no=?)",
        (page_no,),
    )
    con.execute(
        "DELETE FROM reviews WHERE entry_id IN (SELECT id FROM entries WHERE page_no=?)",
        (page_no,),
    )
    con.execute("DELETE FROM entries WHERE page_no=?", (page_no,))

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for i, e in enumerate(entries, start=1):
        lemma = (e.get("lemma_greek") or "??").strip()
        body = e.get("body_markdown") or ""
        papyri = e.get("papyri_citations_raw") or []
        nt = e.get("nt_references_raw") or []
        has_translation = 1 if e.get("has_translation") else 0
        confidence = float(e.get("confidence") or 0.0)
        notes = (e.get("notes") or "").strip()
        # needs_review heuristic: low confidence OR placeholder lemma OR non-empty notes
        needs_review = 1 if (confidence < 0.7 or lemma == "??" or notes) else 0
        con.execute(
            """
            INSERT INTO entries (
                page_no, position_on_page, lemma_greek, lemma_translit,
                strongs, body_markdown, papyri_citations, nt_references,
                has_translation, producer_agent, produced_at, confidence,
                needs_review, source_ocr_agent, source_ocr_at
            ) VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?, 'claude', ?, ?, ?, ?, ?)
            """,
            (
                page_no, i, lemma, body,
                json.dumps(papyri, ensure_ascii=False),
                json.dumps(nt, ensure_ascii=False),
                has_translation, now, confidence, needs_review,
                source_ocr_agent, source_ocr_at,
            ),
        )
        inserted += 1

    return deleted, inserted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="*", help="parser JSON files")
    ap.add_argument("--batch", help="directory of page-*.json files")
    args = ap.parse_args()

    files: list[Path] = []
    if args.batch:
        for f in sorted(Path(args.batch).glob("page-*.json")):
            files.append(f)
    for src in args.inputs:
        files.append(Path(src))

    if not files:
        print("no input files", file=sys.stderr)
        return 1

    con = sqlite3.connect(DB_PATH)
    total_deleted = total_inserted = pages_processed = 0
    try:
        for f in files:
            pn = page_no_from_filename(f)
            if pn is None:
                print(f"skip {f.name}: cannot infer page_no", file=sys.stderr)
                continue
            try:
                payload = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(f"skip {f.name}: invalid JSON: {e}", file=sys.stderr)
                continue
            if not isinstance(payload, list):
                print(f"skip {f.name}: top-level must be JSON array", file=sys.stderr)
                continue
            with con:
                deleted, inserted = ingest_page(con, pn, payload)
            print(f"page {pn}: deleted={deleted} inserted={inserted}")
            total_deleted += deleted
            total_inserted += inserted
            pages_processed += 1
    finally:
        con.close()

    print(
        f"phase2_writer: pages={pages_processed} deleted={total_deleted} inserted={total_inserted}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
