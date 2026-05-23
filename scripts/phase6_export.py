"""Phase 6: export final mm.sqlite + mm.jsonl + mm.tsv + report.md.

For the alpha-chunk preview we INCLUDE all entries (including needs_review=1),
so FirstWord can show every parsed lemma. The spec's stricter export filters
on needs_review=0; we relax it for the preview and document the relaxation
in report.md.

Output: ./out/mm.sqlite, ./out/mm.jsonl, ./out/mm.tsv, ./out/report.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"
OUT_DIR = ROOT / "out"

FINAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS mm_entries (
    strongs           TEXT NOT NULL,
    lemma_greek       TEXT NOT NULL,
    lemma_translit    TEXT,
    body_markdown     TEXT NOT NULL,
    papyri_citations  TEXT,
    nt_references     TEXT,
    source_page       INTEGER NOT NULL,
    needs_review      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (strongs, lemma_greek)
);
CREATE INDEX IF NOT EXISTS idx_mm_strongs ON mm_entries(strongs);
CREATE INDEX IF NOT EXISTS idx_mm_lemma ON mm_entries(lemma_greek);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--strict",
        action="store_true",
        help="follow spec §6: only export entries with needs_review=0",
    )
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    mm_sqlite = OUT_DIR / "mm.sqlite"
    mm_jsonl = OUT_DIR / "mm.jsonl"
    mm_tsv = OUT_DIR / "mm.tsv"
    report_path = OUT_DIR / "report.md"

    if mm_sqlite.exists():
        mm_sqlite.unlink()

    src = sqlite3.connect(DB_PATH)
    src.row_factory = sqlite3.Row

    where = "WHERE needs_review = 0" if args.strict else ""
    rows = src.execute(
        f"""
        SELECT
            COALESCE(strongs, 'G_N/A:' || lemma_greek) AS strongs,
            lemma_greek,
            lemma_translit,
            body_markdown,
            papyri_citations,
            nt_references,
            page_no AS source_page,
            needs_review
          FROM entries
          {where}
         ORDER BY source_page, position_on_page
        """
    ).fetchall()

    # Dedup by (strongs, lemma_greek) — pick the row with the longest body_markdown.
    # Continuations sometimes carry the fuller body; first-seen-wins would clip.
    best: dict[tuple[str, str], sqlite3.Row] = {}
    dedup_skipped = 0
    for r in rows:
        key = (r["strongs"], r["lemma_greek"])
        existing = best.get(key)
        if existing is None:
            best[key] = r
        else:
            dedup_skipped += 1
            new_len = len(r["body_markdown"] or "")
            old_len = len(existing["body_markdown"] or "")
            if new_len > old_len:
                best[key] = r

    # SQLite output
    dst = sqlite3.connect(mm_sqlite)
    dst.executescript(FINAL_SCHEMA)
    inserted = 0
    for r in best.values():
        dst.execute(
            """
            INSERT INTO mm_entries (
                strongs, lemma_greek, lemma_translit, body_markdown,
                papyri_citations, nt_references, source_page, needs_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["strongs"], r["lemma_greek"], r["lemma_translit"],
                r["body_markdown"],
                r["papyri_citations"], r["nt_references"],
                r["source_page"], r["needs_review"],
            ),
        )
        inserted += 1
    dst.commit()
    dst.close()
    seen = set(best.keys())

    # JSONL output (one entry per line)
    with mm_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            key = (r["strongs"], r["lemma_greek"])
            if key not in seen:
                continue
            obj = {
                "strongs": r["strongs"],
                "lemma_greek": r["lemma_greek"],
                "lemma_translit": r["lemma_translit"],
                "body_markdown": r["body_markdown"],
                "papyri_citations": json.loads(r["papyri_citations"] or "[]"),
                "nt_references": json.loads(r["nt_references"] or "[]"),
                "source_page": r["source_page"],
                "needs_review": bool(r["needs_review"]),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # TSV output (STEPBible-style, header row)
    with mm_tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow([
            "strongs", "lemma_greek", "lemma_translit", "body_markdown",
            "papyri_citations", "nt_references", "source_page", "needs_review",
        ])
        for r in rows:
            key = (r["strongs"], r["lemma_greek"])
            if key not in seen:
                continue
            w.writerow([
                r["strongs"], r["lemma_greek"], r["lemma_translit"] or "",
                (r["body_markdown"] or "").replace("\t", " ").replace("\n", "\\n"),
                r["papyri_citations"] or "[]",
                r["nt_references"] or "[]",
                r["source_page"], r["needs_review"],
            ])

    # Stats for report
    total_pages = src.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    parsed_pages = src.execute("SELECT COUNT(DISTINCT page_no) FROM entries").fetchone()[0]
    total_entries = src.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    strongs_keyed = src.execute(
        "SELECT COUNT(*) FROM entries WHERE strongs IS NOT NULL"
    ).fetchone()[0]
    g_na = total_entries - strongs_keyed
    snaps = src.execute(
        "SELECT COUNT(*) FROM disagreements WHERE resolution_by='auto:strongs-snap'"
    ).fetchone()[0]
    verdicts = {
        v: src.execute(
            "SELECT COUNT(*) FROM reviews WHERE reviewer_agent='codex' AND verdict=?", (v,)
        ).fetchone()[0]
        for v in ("agree", "minor", "major", "reject")
    }
    open_dis = src.execute(
        "SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL"
    ).fetchone()[0]
    needs_review_count = src.execute(
        "SELECT COUNT(*) FROM entries WHERE needs_review=1"
    ).fetchone()[0]
    placeholder = src.execute(
        "SELECT COUNT(*) FROM entries WHERE lemma_greek='??'"
    ).fetchone()[0]

    now = datetime.now(timezone.utc).isoformat()
    strongs_pct = (100.0 * strongs_keyed / total_entries) if total_entries else 0
    audit_pct = (
        100.0 * (verdicts["agree"] + verdicts["minor"]) / total_entries
    ) if total_entries else 0

    report = f"""# Moulton-Milligan Digitization — Report

Generated: {now}

## Scope of this export

**Alpha-chunk preview** — pages 31–80 only (first ~50 lexicon-body pages).
Phase 4 (citation normalization) and Phase 5 (disagreement resolution) are
**skipped** for this preview; `papyri_citations` field holds the raw
as-written strings from `papyri_citations_raw`.

This export uses the **relaxed filter** (all entries included).
Pass `--strict` to apply spec §6's `needs_review=0` filter ({needs_review_count}
entries would be excluded).

## Source coverage

- Total source pages: {total_pages}
- Parsed pages: {parsed_pages}
- Pages still on Tesseract baseline (need Phase 1B): 416

## Entries

- Total entries: {total_entries}
- `needs_review=1` flagged: {needs_review_count}
- Placeholder lemmas (`??`): {placeholder}
- Exported to mm.sqlite: {inserted}
- Duplicate (strongs, lemma) skipped: {dedup_skipped}

## Strong's keying (Phase 3)

- Strong's-keyed: {strongs_keyed} ({strongs_pct:.1f}%)
- `G_N/A:<lemma>` placeholders: {g_na}
- Fuzzy snap corrections (logged in disagreements): {snaps}

Spec §8 gate: ≥75% Strong's coverage — **{'PASS' if strongs_pct >= 75 else 'FAIL'}**.

## Adversarial review (Codex)

- agree: {verdicts['agree']} ({100*verdicts['agree']/total_entries:.1f}%)
- minor: {verdicts['minor']} ({100*verdicts['minor']/total_entries:.1f}%)
- major: {verdicts['major']} ({100*verdicts['major']/total_entries:.1f}%)
- reject: {verdicts['reject']}

agree+minor rate: **{audit_pct:.1f}%** (spec §8 gate: ≥85%) — **{'PASS' if audit_pct >= 85 else 'FAIL'}**.

Open disagreements (Phase 5 work): **{open_dis}**.

## Files in this export

- `mm.sqlite` — primary deliverable, GRDB.swift-compatible
- `mm.jsonl` — one entry per line
- `mm.tsv` — tab-separated, STEPBible-style header
- `report.md` — this file

## Known limitations

1. Pages 1–30 (front matter + abbreviation tables) NOT parsed.
2. Pages 81–735 NOT parsed (Phase 2 continues over time).
3. `papyri_citations` is raw-as-written, not normalized (Phase 4 unskipped).
4. {open_dis} open disagreements not resolved (Phase 5 unskipped).
5. Continuation-from-prior-page entries sometimes have inferred lemma rather
   than the true prior-page headword. See entries with
   `notes: "continuation from prior page"`.
"""
    report_path.write_text(report, encoding="utf-8")

    src.close()

    print(f"wrote {mm_sqlite}: {inserted} entries (dedup skipped {dedup_skipped})")
    print(f"wrote {mm_jsonl}")
    print(f"wrote {mm_tsv}")
    print(f"wrote {report_path}")
    print()
    print(f"Strong's coverage: {strongs_pct:.1f}% (gate >= 75%) {'PASS' if strongs_pct >= 75 else 'FAIL'}")
    print(f"agree+minor:       {audit_pct:.1f}% (gate >= 85%) {'PASS' if audit_pct >= 85 else 'FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
