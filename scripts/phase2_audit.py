"""Phase 2 auditor: run Codex on parsed pages, write verdicts to `reviews`.

For each page passed in (`--pages 1,2,3` or `--all-unaudited`), pulls:
- The page markdown (`pages.ocr_text`)
- The parser-emitted entries (`entries.* WHERE page_no=N` ordered by position_on_page)

Builds an auditor prompt from scripts/phase2_prompts.AUDITOR_PROMPT, calls
`codex_call.codex_exec`, parses the returned JSON, and writes one `reviews`
row per parser entry. Disagreements ≥ `minor` are also recorded in
`disagreements` for Phase 5 resolution.

Skip behavior:
- A page with all entries already reviewed by 'codex' is skipped (idempotent).
- A page with partial review coverage is fully re-audited (replaces prior reviews).

Codex output is expected to be a single JSON object. If the model wraps it
in ```json fences or includes leading commentary, we strip those defensively
before json.loads.

Usage:
  python scripts/phase2_audit.py --pages 1,2,3
  python scripts/phase2_audit.py --all-unaudited [--first N]
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
sys.path.insert(0, str(ROOT / "scripts"))

from codex_call import codex_exec  # noqa: E402
from phase2_prompts import AUDITOR_PROMPT  # noqa: E402

DB_PATH = ROOT / "state" / "run.sqlite"

JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> dict | None:
    """Pull a JSON object out of model output, tolerating fences/prefixes."""
    if not text:
        return None
    candidates: list[str] = []
    m = JSON_FENCE.search(text)
    if m:
        candidates.append(m.group(1))
    # Also try the whole text and the substring from the first `{`
    candidates.append(text)
    first_brace = text.find("{")
    if first_brace > 0:
        candidates.append(text[first_brace:])
    for c in candidates:
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            continue
    return None


def already_fully_reviewed(con: sqlite3.Connection, page_no: int) -> bool:
    row = con.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM entries WHERE page_no=?) AS n_entries,
          (SELECT COUNT(*) FROM reviews r
             JOIN entries e ON e.id=r.entry_id
            WHERE e.page_no=? AND r.reviewer_agent='codex') AS n_reviews
        """,
        (page_no, page_no),
    ).fetchone()
    n_entries, n_reviews = row
    return n_entries > 0 and n_reviews >= n_entries


def fetch_entries(con: sqlite3.Connection, page_no: int) -> list[dict]:
    rows = con.execute(
        """
        SELECT id, position_on_page, lemma_greek, body_markdown,
               papyri_citations, nt_references, has_translation,
               confidence
          FROM entries
         WHERE page_no=?
         ORDER BY position_on_page
        """,
        (page_no,),
    ).fetchall()
    return [
        {
            "entry_id": r[0],
            "parser_position": r[1],
            "lemma_greek": r[2],
            "body_markdown": r[3],
            "papyri_citations_raw": json.loads(r[4] or "[]"),
            "nt_references_raw": json.loads(r[5] or "[]"),
            "has_translation": bool(r[6]),
            "confidence": r[7],
        }
        for r in rows
    ]


def audit_page(con: sqlite3.Connection, page_no: int, *, timeout: int = 240) -> dict:
    """Returns a small summary dict (entry_count, verdicts breakdown)."""
    page_row = con.execute(
        "SELECT ocr_text FROM pages WHERE page_no=?", (page_no,)
    ).fetchone()
    if not page_row:
        return {"page_no": page_no, "error": "missing page row"}
    ocr_text = page_row[0] or ""

    entries = fetch_entries(con, page_no)
    if not entries:
        return {"page_no": page_no, "error": "no entries to audit"}

    parser_json = json.dumps(entries, ensure_ascii=False, indent=2)
    prompt = AUDITOR_PROMPT.format(
        page_no=page_no,
        ocr_text=ocr_text,
        parser_json=parser_json,
    )

    raw = codex_exec(prompt, timeout=timeout)
    if not raw:
        return {"page_no": page_no, "error": "codex_exec returned no output"}
    payload = extract_json(raw)
    if not payload or "verdicts" not in payload:
        return {
            "page_no": page_no,
            "error": "could not parse JSON from codex output",
            "raw_head": raw[:200],
        }

    verdicts = payload["verdicts"]
    now = datetime.now(timezone.utc).isoformat()
    breakdown = {"agree": 0, "minor": 0, "major": 0, "reject": 0, "unknown": 0}

    # Replace prior reviews for these entries
    entry_ids = [e["entry_id"] for e in entries]
    placeholders = ",".join("?" for _ in entry_ids)
    con.execute(
        f"DELETE FROM disagreements WHERE entry_id IN ({placeholders})", entry_ids
    )
    con.execute(
        f"DELETE FROM reviews WHERE entry_id IN ({placeholders}) AND reviewer_agent='codex'",
        entry_ids,
    )

    for v in verdicts:
        pos = v.get("parser_position")
        verdict = (v.get("verdict") or "").lower()
        if verdict not in breakdown:
            verdict = "unknown"
        breakdown[verdict] += 1

        # Map position to entry_id
        entry = next((e for e in entries if e["parser_position"] == pos), None)
        if not entry:
            continue
        reviewer_lemma = v.get("reviewer_lemma")
        field_diffs = v.get("field_diffs") or {}
        notes = v.get("notes") or ""

        con.execute(
            """
            INSERT INTO reviews (entry_id, reviewer_agent, verdict, diff,
                                 reviewer_lemma, reviewer_strongs, notes, reviewed_at)
            VALUES (?, 'codex', ?, ?, ?, NULL, ?, ?)
            """,
            (
                entry["entry_id"], verdict,
                json.dumps(field_diffs, ensure_ascii=False),
                reviewer_lemma, notes, now,
            ),
        )

        if verdict in ("minor", "major", "reject"):
            for field, vals in field_diffs.items():
                con.execute(
                    """
                    INSERT INTO disagreements (
                        entry_id, field, producer_value, reviewer_value,
                        resolution, resolution_by, resolved_at
                    ) VALUES (?, ?, ?, ?, NULL, NULL, NULL)
                    """,
                    (
                        entry["entry_id"], field,
                        (vals or {}).get("producer"),
                        (vals or {}).get("reviewer"),
                    ),
                )

    return {"page_no": page_no, "entries": len(entries), "breakdown": breakdown}


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pages", help="comma-separated page numbers (e.g. 1,2,3)")
    g.add_argument("--all-unaudited", action="store_true")
    ap.add_argument("--first", type=int, default=None, help="cap pages")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--skip-already-reviewed", action="store_true", default=True)
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    if args.pages:
        page_nos = [int(p) for p in args.pages.split(",") if p.strip()]
    else:
        rows = con.execute(
            """
            SELECT DISTINCT e.page_no
              FROM entries e
              LEFT JOIN reviews r
                ON r.entry_id = e.id AND r.reviewer_agent = 'codex'
             GROUP BY e.page_no
            HAVING COUNT(r.id) < COUNT(e.id)
             ORDER BY e.page_no
            """
        ).fetchall()
        page_nos = [r[0] for r in rows]

    if args.first:
        page_nos = page_nos[: args.first]
    if not page_nos:
        print("no pages to audit")
        return 0

    print(f"auditing {len(page_nos)} page(s): {page_nos[:10]}{'...' if len(page_nos) > 10 else ''}")
    try:
        for pn in page_nos:
            if args.skip_already_reviewed and already_fully_reviewed(con, pn):
                print(f"page {pn}: already fully reviewed by codex, skip")
                continue
            with con:
                summary = audit_page(con, pn, timeout=args.timeout)
            print(f"page {pn}: {summary}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
