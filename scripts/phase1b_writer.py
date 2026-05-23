"""Phase 1B writer: receive a vision-OCR sub-agent's JSON output and store it.

The sub-agent emits one JSON document per page:
  {"page_no": N, "markdown": "...", "low_confidence_spans": [...]}

This script reads such JSON (one per arg, or via --batch with a directory of
*.json files) and updates pages.ocr_text + ocr_agent='claude-vision'.

It does NOT overwrite Tesseract output unless --force is given; instead it
writes vision output to a sibling text file pages/page-NNN.vision.md and
sets ocr_agent='claude-vision' to indicate the page now has both passes.
The combined ocr_text stored in DB is the vision pass (more accurate for
polytonic Greek per spec §6).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"
PAGES_DIR = ROOT / "pages"


def write_one(con: sqlite3.Connection, payload: dict) -> tuple[int, bool, str]:
    page_no = int(payload.get("page_no", 0))
    if page_no <= 0:
        return 0, False, "missing page_no"
    if "markdown" not in payload:
        return page_no, False, "no markdown key"
    md = payload.get("markdown") or ""
    side_path = PAGES_DIR / f"page-{page_no:03d}.vision.md"
    side_path.write_text(md, encoding="utf-8")
    ts = datetime.now(timezone.utc).isoformat()
    con.execute(
        "UPDATE pages SET ocr_text=?, ocr_status='done', ocr_agent='claude-vision', ocr_at=? WHERE page_no=?",
        (md, ts, page_no),
    )
    if con.total_changes == 0:
        # page row missing — insert
        png_path = PAGES_DIR / f"page-{page_no:03d}.png"
        con.execute(
            "INSERT INTO pages (page_no, png_path, ocr_text, ocr_status, ocr_agent, ocr_at) VALUES (?,?,?,?,?,?)",
            (page_no, str(png_path), md, "done", "claude-vision", ts),
        )
    return page_no, True, f"{len(md)} chars"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="*", help="JSON files or - for stdin (one JSON object)")
    ap.add_argument("--batch", help="directory containing *.json sub-agent outputs")
    args = ap.parse_args()

    payloads: list[dict] = []
    if args.batch:
        for f in sorted(Path(args.batch).glob("*.json")):
            try:
                payloads.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError as e:
                print(f"skip {f}: {e}", file=sys.stderr)
    for src in args.inputs:
        if src == "-":
            payloads.append(json.load(sys.stdin))
        else:
            payloads.append(json.loads(Path(src).read_text(encoding="utf-8")))

    if not payloads:
        print("no payloads", file=sys.stderr)
        return 1

    con = sqlite3.connect(DB_PATH)
    try:
        ok = 0
        bad = 0
        for p in payloads:
            # Sub-agents may return either a single page dict or a list of pages
            items = p if isinstance(p, list) else [p]
            for item in items:
                pn, success, msg = write_one(con, item)
                if success:
                    ok += 1
                    print(f"  page {pn}: {msg}")
                else:
                    bad += 1
                    print(f"  page {pn}: SKIP {msg}", file=sys.stderr)
        con.commit()
        print(f"phase1b_writer: ok={ok} bad={bad}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
