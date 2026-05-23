"""Quick Phase 2 status snapshot. No args.

Reports:
- pages parsed vs. unparsed (and how many of unparsed are still tesseract-only)
- entries totals (with confidence buckets)
- review coverage (codex verdicts breakdown)
- disagreement counts
- reparse backlog (pages whose OCR upgraded after parse)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    total_pages = c.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    parsed_pages = c.execute(
        "SELECT COUNT(DISTINCT page_no) FROM entries"
    ).fetchone()[0]
    unparsed_vision = c.execute(
        """
        SELECT COUNT(*) FROM pages p
         WHERE p.ocr_agent='claude-vision' AND p.ocr_status='done'
           AND NOT EXISTS (SELECT 1 FROM entries e WHERE e.page_no=p.page_no)
        """
    ).fetchone()[0]
    unparsed_tess = c.execute(
        """
        SELECT COUNT(*) FROM pages p
         WHERE p.ocr_agent='tesseract' AND p.ocr_status='done'
           AND NOT EXISTS (SELECT 1 FROM entries e WHERE e.page_no=p.page_no)
        """
    ).fetchone()[0]

    print("=== Pages ===")
    print(f"  total:                       {total_pages}")
    print(f"  parsed (have entries):       {parsed_pages}")
    print(f"  unparsed, claude-vision OCR: {unparsed_vision}  <- ready for Phase 2")
    print(f"  unparsed, tesseract OCR:     {unparsed_tess}    <- needs 1B first (or parse with caveat)")

    total_entries = c.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    high_conf = c.execute("SELECT COUNT(*) FROM entries WHERE confidence >= 0.9").fetchone()[0]
    mid_conf = c.execute("SELECT COUNT(*) FROM entries WHERE confidence >= 0.7 AND confidence < 0.9").fetchone()[0]
    low_conf = c.execute("SELECT COUNT(*) FROM entries WHERE confidence < 0.7").fetchone()[0]
    placeholder = c.execute("SELECT COUNT(*) FROM entries WHERE lemma_greek='??'").fetchone()[0]
    needs_review = c.execute("SELECT COUNT(*) FROM entries WHERE needs_review=1").fetchone()[0]

    print()
    print("=== Entries ===")
    print(f"  total:        {total_entries}")
    print(f"  confidence >= 0.9: {high_conf}")
    print(f"  0.7 - 0.9:         {mid_conf}")
    print(f"  < 0.7:             {low_conf}")
    print(f"  placeholder ('??'): {placeholder}")
    print(f"  flagged needs_review: {needs_review}")

    total_reviews = c.execute("SELECT COUNT(*) FROM reviews WHERE reviewer_agent='codex'").fetchone()[0]
    verdicts = {
        v: c.execute("SELECT COUNT(*) FROM reviews WHERE reviewer_agent='codex' AND verdict=?", (v,)).fetchone()[0]
        for v in ("agree", "minor", "major", "reject")
    }
    print()
    print("=== Codex Reviews ===")
    print(f"  total: {total_reviews}")
    if total_entries:
        coverage = 100.0 * total_reviews / total_entries
        print(f"  coverage: {coverage:.1f}% of entries")
    for v, n in verdicts.items():
        pct = (100.0 * n / total_reviews) if total_reviews else 0.0
        print(f"  {v}: {n} ({pct:.1f}%)")

    n_dis_open = c.execute(
        "SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL"
    ).fetchone()[0]
    n_dis_resolved = c.execute(
        "SELECT COUNT(*) FROM disagreements WHERE resolution IS NOT NULL"
    ).fetchone()[0]
    print()
    print("=== Disagreements ===")
    print(f"  open:     {n_dis_open}")
    print(f"  resolved: {n_dis_resolved}")

    reparse = c.execute(
        """
        SELECT COUNT(DISTINCT e.page_no)
          FROM entries e
          JOIN pages p ON p.page_no = e.page_no
         WHERE e.source_ocr_agent IS NOT NULL
           AND e.source_ocr_agent != p.ocr_agent
        """
    ).fetchone()[0]
    print()
    print("=== Reparse backlog (OCR upgraded since parse) ===")
    print(f"  pages awaiting reparse: {reparse}")


if __name__ == "__main__":
    main()
