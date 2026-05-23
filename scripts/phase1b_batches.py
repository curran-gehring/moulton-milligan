"""Phase 1B helper: emit a list of (batch_id, page_no[]) for vision-OCR dispatch.

Usage:
  python scripts/phase1b_batches.py [--batch-size 10] [--first N]

Prints JSON to stdout that the orchestrator (Claude Code main) reads, then
spawns N parallel Task subagents — one per batch — to do the vision OCR
re-pass per spec §6 Phase 1B.

A page is "needing vision OCR" when:
  - ocr_status='done' AND ocr_agent='tesseract'  (tesseract-only so far)
  - OR ocr_status='failed' / 'pending'           (recovery)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--first", type=int, default=None, help="cap total pages")
    ap.add_argument("--max-batches", type=int, default=None, help="cap batches emitted")
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        """
        SELECT page_no, png_path
          FROM pages
         WHERE ocr_agent != 'claude-vision' OR ocr_agent IS NULL OR ocr_status != 'done'
         ORDER BY page_no
        """
    ).fetchall()
    con.close()

    if args.first:
        rows = rows[: args.first]
    batches = []
    for i in range(0, len(rows), args.batch_size):
        chunk = rows[i : i + args.batch_size]
        batches.append({
            "batch_id": f"b{i // args.batch_size:04d}",
            "pages": [{"page_no": p, "png_path": pp} for p, pp in chunk],
        })
    if args.max_batches:
        batches = batches[: args.max_batches]
    json.dump({"total_pages": len(rows), "batches": batches}, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
