"""Phase 5: deterministically resolve auto-classifiable disagreements.

For each open `disagreements` row, walk the policy chain in order. The first
policy that matches wins. A matched policy returns:
- a one-line `resolution` string (audit trail)
- a `resolution_by` tag (e.g. `auto:reviewer-superset-citations`)
- optionally an `entry_field` + `entry_value` to overwrite on the entries row

Policies (deterministic, no LLM):
1. lemma-strip-period       — reviewer differs only by trailing `.` → keep producer
2. notes-continuation       — producer empty, reviewer flags continuation → close
3. citations-superset       — apply set-superset rule to papyri_citations_raw
4. body-summary-diff        — auditor returned style descriptors, not body → keep producer
5. has-translation-from-body — re-derive flag from body via quoted-gloss heuristic

Anything else is left open and surfaces in the manual queue.

Idempotent: only touches rows where `resolution IS NULL`.

Usage:
  python scripts/phase5_resolve.py --dry-run
  python scripts/phase5_resolve.py
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s) if s else s


def parse_citations(v: str | None) -> list[str]:
    """Parse a citation value (JSON list string or `;`-separated string) → list[str]."""
    if v is None:
        return []
    s = v.strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [str(x).strip() for x in arr if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [p.strip() for p in s.split(";") if p.strip()]


def canon_token(t: str) -> str:
    """Normalize a citation for set comparison: NFC, strip wrapping `*` and punctuation, lower."""
    t = nfc(t).strip()
    t = re.sub(r"^[\*\.\,\;\s]+|[\*\.\,\;\s]+$", "", t)
    return t.lower()


# --- Policy registry ---------------------------------------------------------

POLICIES: list[tuple[str, callable]] = []


def policy(name: str):
    def deco(fn):
        POLICIES.append((name, fn))
        return fn
    return deco


@policy("lemma-strip-period")
def lemma_strip_period(d: dict, entry: dict) -> dict | None:
    if d["field"] != "lemma_greek":
        return None
    p = (d["producer_value"] or "").strip()
    r = (d["reviewer_value"] or "").strip()
    if p and r and r == p + ".":
        return {
            "resolution": "keep producer (bare lemma, no trailing period)",
            "resolution_by": "auto:lemma-strip-period",
            "entry_field": None,
            "entry_value": None,
        }
    return None


@policy("notes-continuation")
def notes_continuation(d: dict, entry: dict) -> dict | None:
    if d["field"] != "notes":
        return None
    p = (d["producer_value"] or "").strip()
    r = (d["reviewer_value"] or "").strip()
    if p == "" and r.lower().startswith("continuation"):
        return {
            "resolution": f"accept reviewer note: {r!r}",
            "resolution_by": "auto:accept-reviewer-note",
            "entry_field": None,
            "entry_value": None,
        }
    return None


@policy("citations-superset")
def citations_superset(d: dict, entry: dict) -> dict | None:
    # Intentionally only papyri_citations_raw; nt_references_raw stays manual
    # (its semantic disputes are too risky to auto-resolve from set comparison).
    if d["field"] != "papyri_citations_raw":
        return None
    p_list = parse_citations(d["producer_value"])
    r_list = parse_citations(d["reviewer_value"])
    p_set = {canon_token(x) for x in p_list if x}
    r_set = {canon_token(x) for x in r_list if x}
    if not p_set and not r_set:
        return None
    if p_set == r_set:
        return {
            "resolution": "set-equal after normalization; keep producer formatting",
            "resolution_by": "auto:set-equal-keep-producer",
            "entry_field": None,
            "entry_value": None,
        }
    if p_set < r_set:
        added = sorted(r_set - p_set)
        return {
            "resolution": f"reviewer adds {len(added)} citation(s); apply reviewer list",
            "resolution_by": "auto:reviewer-superset-citations",
            "entry_field": "papyri_citations",
            "entry_value": json.dumps(r_list, ensure_ascii=False),
        }
    if r_set < p_set:
        dropped = sorted(p_set - r_set)
        return {
            "resolution": f"reviewer drops {len(dropped)} citation(s); keep producer",
            "resolution_by": "auto:producer-superset-citations",
            "entry_field": None,
            "entry_value": None,
        }
    return None


BODY_DESCRIPTOR_WORDS = re.compile(
    r"\b(ASCII|curly|straight|quotation|quotes?|apostrophe|punctuation|"
    r"spacing|italics|whitespace|hyphen|dash|diaeresis|capitalization|"
    r"smartquotes?|markup|formatting|Deissmann)\b",
    re.IGNORECASE,
)


@policy("body-summary-diff")
def body_summary_diff(d: dict, entry: dict) -> dict | None:
    if d["field"] != "body_markdown":
        return None
    p = d["producer_value"] or ""
    r = d["reviewer_value"] or ""
    if len(p) > 250 or len(r) > 250:
        return None
    if any(0x0370 <= ord(c) <= 0x03FF for c in p + r):
        return None
    if BODY_DESCRIPTOR_WORDS.search(p) or BODY_DESCRIPTOR_WORDS.search(r):
        return {
            "resolution": "auditor returned style descriptor, not body content; keep producer body",
            "resolution_by": "auto:summary-diff-not-content",
            "entry_field": None,
            "entry_value": None,
        }
    return None


@policy("has-translation-from-body")
def has_translation_from_body(d: dict, entry: dict) -> dict | None:
    if d["field"] != "has_translation":
        return None
    body = entry["body_markdown"] or ""
    has_quoted_gloss = bool(re.search(r'["“‘][A-Za-z]', body))
    new_val = 1 if has_quoted_gloss else 0
    cur = entry.get("has_translation", 0) or 0
    if new_val != cur:
        return {
            "resolution": f"body heuristic (quoted English gloss) → has_translation={bool(new_val)} (was {bool(cur)})",
            "resolution_by": "auto:has-translation-from-body",
            "entry_field": "has_translation",
            "entry_value": new_val,
        }
    return {
        "resolution": f"body heuristic confirms current has_translation={bool(cur)}",
        "resolution_by": "auto:has-translation-from-body",
        "entry_field": None,
        "entry_value": None,
    }


# --- Driver ------------------------------------------------------------------


def apply_policies(con: sqlite3.Connection, dry_run: bool):
    rows = con.execute(
        """
        SELECT d.id AS did, d.entry_id, d.field, d.producer_value, d.reviewer_value,
               e.lemma_greek, e.body_markdown, e.has_translation,
               e.papyri_citations, e.nt_references, e.page_no
          FROM disagreements d
          JOIN entries e ON e.id = d.entry_id
         WHERE d.resolution IS NULL
         ORDER BY d.id
        """
    ).fetchall()

    summary: dict[str, int] = {}
    skipped: list[tuple] = []
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        d = {
            "did": row["did"],
            "entry_id": row["entry_id"],
            "field": row["field"],
            "producer_value": row["producer_value"],
            "reviewer_value": row["reviewer_value"],
        }
        entry = {
            "id": row["entry_id"],
            "lemma_greek": row["lemma_greek"],
            "body_markdown": row["body_markdown"],
            "has_translation": row["has_translation"],
            "papyri_citations": row["papyri_citations"],
            "nt_references": row["nt_references"],
            "page_no": row["page_no"],
        }

        result = None
        for _name, fn in POLICIES:
            result = fn(d, entry)
            if result:
                break

        if not result:
            skipped.append(
                (
                    d["did"],
                    entry["page_no"],
                    d["field"],
                    (d["producer_value"] or "")[:80],
                    (d["reviewer_value"] or "")[:80],
                )
            )
            key = f"SKIP:{d['field']}"
            summary[key] = summary.get(key, 0) + 1
            continue

        summary[result["resolution_by"]] = summary.get(result["resolution_by"], 0) + 1

        if dry_run:
            continue

        if result["entry_field"]:
            con.execute(
                f"UPDATE entries SET {result['entry_field']}=? WHERE id=?",
                (result["entry_value"], entry["id"]),
            )
        con.execute(
            "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=?",
            (result["resolution"], result["resolution_by"], now, d["did"]),
        )

    return summary, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="don't write changes")
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        with con:
            summary, skipped = apply_policies(con, dry_run=args.dry_run)
    finally:
        con.close()

    print(f"\n=== Phase 5 resolution summary (dry_run={args.dry_run}) ===")
    total_resolved = sum(v for k, v in summary.items() if not k.startswith("SKIP"))
    total_skipped = sum(v for k, v in summary.items() if k.startswith("SKIP"))
    for k in sorted(summary):
        print(f"  {k:45} {summary[k]}")
    print(f"\n  resolved: {total_resolved}")
    print(f"  skipped:  {total_skipped}")

    if skipped:
        print(f"\nSkipped (manual) — showing first 40:")
        for did, page, field, pv, rv in skipped[:40]:
            print(f"  d#{did:4} p{page:3} {field:22} PROD={pv!r}")
            print(f"                                  REV ={rv!r}")
        if len(skipped) > 40:
            print(f"  ... and {len(skipped) - 40} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
