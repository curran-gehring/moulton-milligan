"""Phase 2 dispatcher: emit a manifest of pages ready for entry parsing.

Selection logic:
- Pages with `ocr_status='done'` AND no entries yet → parse fresh.
- Pages with entries whose `source_ocr_agent` differs from current
  `pages.ocr_agent` → reparse (the OCR has upgraded since the last parse).

Output: JSON to stdout (or `--out`) with shape:
{
  "generated_at": "<iso>",
  "pages": [
    {
      "page_no": 1,
      "ocr_text": "...",
      "source_ocr_agent": "claude-vision",
      "source_ocr_at": "...",
      "reparse": false  # true if old entries exist and need deletion before re-insert
    }, ...
  ]
}

Usage:
  python scripts/phase2_dispatch.py [--first N] [--from PAGE] [--to PAGE] [--out FILE]
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=None, help="cap pages emitted")
    ap.add_argument("--from", dest="page_from", type=int, default=None)
    ap.add_argument("--to", dest="page_to", type=int, default=None)
    ap.add_argument("--out", default=None, help="output JSON file (default: stdout)")
    ap.add_argument(
        "--include-tesseract",
        action="store_true",
        help="include pages whose OCR is still tesseract baseline (default: vision only)",
    )
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Pages with no entries yet (fresh-parse candidates)
    where_ocr = "p.ocr_status='done'"
    if not args.include_tesseract:
        where_ocr += " AND p.ocr_agent='claude-vision'"
    if args.page_from is not None:
        where_ocr += f" AND p.page_no >= {int(args.page_from)}"
    if args.page_to is not None:
        where_ocr += f" AND p.page_no <= {int(args.page_to)}"

    fresh = con.execute(
        f"""
        SELECT p.page_no, p.ocr_text, p.ocr_agent, p.ocr_at
          FROM pages p
         WHERE {where_ocr}
           AND NOT EXISTS (SELECT 1 FROM entries e WHERE e.page_no = p.page_no)
         ORDER BY p.page_no
        """
    ).fetchall()

    # Pages where entries exist but OCR has upgraded since parse (reparse candidates)
    reparse = con.execute(
        f"""
        SELECT DISTINCT p.page_no, p.ocr_text, p.ocr_agent, p.ocr_at
          FROM pages p
          JOIN entries e ON e.page_no = p.page_no
         WHERE {where_ocr}
           AND e.source_ocr_agent IS NOT NULL
           AND e.source_ocr_agent != p.ocr_agent
         ORDER BY p.page_no
        """
    ).fetchall()

    pages = []
    for row in fresh:
        pages.append({
            "page_no": row["page_no"],
            "ocr_text": row["ocr_text"] or "",
            "source_ocr_agent": row["ocr_agent"],
            "source_ocr_at": row["ocr_at"],
            "reparse": False,
        })
    for row in reparse:
        pages.append({
            "page_no": row["page_no"],
            "ocr_text": row["ocr_text"] or "",
            "source_ocr_agent": row["ocr_agent"],
            "source_ocr_at": row["ocr_at"],
            "reparse": True,
        })

    pages.sort(key=lambda p: p["page_no"])
    if args.first:
        pages = pages[: args.first]

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fresh_count": sum(1 for p in pages if not p["reparse"]),
        "reparse_count": sum(1 for p in pages if p["reparse"]),
        "total": len(pages),
        "pages": pages,
    }

    out = json.dumps(manifest, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        # Brief summary to stderr so the orchestrator sees it
        print(
            f"wrote {args.out}: {manifest['total']} pages "
            f"({manifest['fresh_count']} fresh, {manifest['reparse_count']} reparse)",
            file=sys.stderr,
        )
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
