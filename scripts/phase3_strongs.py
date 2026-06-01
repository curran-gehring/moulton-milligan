"""Phase 3: Strong's keying with snap-correction.

For each row in `entries` where `strongs IS NULL`:
1. Strip trailing period(s) + whitespace from lemma_greek.
2. NFC-normalize.
3. Exact match against the variant set built from reference/strongs_lemma_index.json.
4. If no exact match, rapidfuzz fuzzy match against the full lemma+variants pool
   with edit-distance <= 2 (configurable). Snap-corrected; original logged.
5. Otherwise, leave strongs as NULL (Phase 6 export uses `G_N/A:<lemma>` placeholder).

Writes `entries.strongs` and `entries.lemma_translit`. Also records snap-corrections
in `disagreements` table with `resolution_by='auto:strongs-snap'`.

Per spec §6 Phase 3, the Codex audit step on snap-corrections is RECOMMENDED but
not blocking. We skip it for the alpha-chunk preview — Phase 5 picks it up later.

Usage:
  python scripts/phase3_strongs.py [--dry-run] [--threshold 2]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"
INDEX_PATH = ROOT / "reference" / "strongs_lemma_index.json"

try:
    from rapidfuzz import process, fuzz
    from rapidfuzz.distance import Levenshtein
except ImportError:
    print("Need rapidfuzz: pip install rapidfuzz", file=sys.stderr)
    sys.exit(1)


def normalize(s: str) -> str:
    """NFC + strip trailing period/whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s).strip()
    while s.endswith("."):
        s = s[:-1].strip()
    return s


def load_index(path: Path) -> tuple[dict[str, str], dict[str, dict]]:
    """Returns (variant -> strongs_id, strongs_id -> entry_dict).

    Multiple Strong's IDs can share a variant string in rare cases; we pick the
    lowest-numbered. Log collisions for transparency.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    variant_to_id: dict[str, str] = {}
    collisions: dict[str, list[str]] = defaultdict(list)
    for sid, info in raw.items():
        variants = set(info.get("variants") or [])
        variants.add(info.get("lemma") or "")
        for v in variants:
            v_n = normalize(v)
            if not v_n:
                continue
            if v_n in variant_to_id and variant_to_id[v_n] != sid:
                collisions[v_n].append(sid)
                # Keep lowest-numbered
                if sid < variant_to_id[v_n]:
                    variant_to_id[v_n] = sid
            else:
                variant_to_id[v_n] = sid
    if collisions:
        print(
            f"index: {len(collisions)} variant collisions (using lowest-numbered ID for each)",
            file=sys.stderr,
        )
    return variant_to_id, raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--threshold",
        type=int,
        default=2,
        help="max edit distance for fuzzy snap (default 2)",
    )
    ap.add_argument(
        "--first",
        type=int,
        default=None,
        help="process only first N entries (debug)",
    )
    ap.add_argument(
        "--from",
        dest="page_from",
        type=int,
        default=None,
        help="only key entries on pages >= this (avoids disturbing prior-phase decisions)",
    )
    ap.add_argument(
        "--to",
        dest="page_to",
        type=int,
        default=None,
        help="only key entries on pages <= this",
    )
    args = ap.parse_args()

    variant_to_id, index = load_index(INDEX_PATH)
    print(f"loaded {len(index)} Strong's IDs, {len(variant_to_id)} unique variants")

    pool = list(variant_to_id.keys())  # for rapidfuzz extractOne

    con = sqlite3.connect(DB_PATH)
    where = "strongs IS NULL"
    params: list = []
    if args.page_from is not None:
        where += " AND page_no >= ?"
        params.append(args.page_from)
    if args.page_to is not None:
        where += " AND page_no <= ?"
        params.append(args.page_to)
    # Don't re-snap lemmas a human already adjudicated to G_N/A. A NULL entry that
    # carries a manual:strongs-fix disagreement RESOLVED TO G_N/A was DELIBERATELY
    # left unkeyed (e.g. a bad fuzzy snap reverted: ἀπαρτίζω, ἄπορος). Without this
    # guard every phase3 run silently re-introduces the exact snap that was reverted.
    # Scope to reviewer_value='G_N/A' so a manual:strongs-fix that set a REAL key
    # (e.g. ἀπογίνομαι->G0581) never tombstones, and a later lemma_swap that clears
    # the tombstone can still be re-keyed. NOT EXISTS (not NOT IN) to avoid NULL
    # poisoning if any disagreements.entry_id is NULL.
    where += (
        " AND NOT EXISTS (SELECT 1 FROM disagreements d "
        "WHERE d.entry_id = entries.id "
        "AND d.resolution_by='manual:strongs-fix' AND d.reviewer_value='G_N/A')"
    )
    rows = con.execute(
        f"""
        SELECT id, page_no, position_on_page, lemma_greek
          FROM entries
         WHERE {where}
         ORDER BY page_no, position_on_page
        """,
        params,
    ).fetchall()
    if args.first:
        rows = rows[: args.first]
    print(f"entries to key: {len(rows)}")

    now = datetime.now(timezone.utc).isoformat()
    exact = fuzzy = unmatched = placeholder = 0

    for entry_id, page_no, pos, lemma in rows:
        original = lemma or ""
        if original.strip() == "??":
            placeholder += 1
            continue

        normalized = normalize(original)
        if not normalized:
            placeholder += 1
            continue

        # 1) exact match
        sid = variant_to_id.get(normalized)
        if sid:
            translit = index[sid].get("translit")
            if not args.dry_run:
                con.execute(
                    "UPDATE entries SET strongs=?, lemma_translit=? WHERE id=?",
                    (sid, translit, entry_id),
                )
            exact += 1
            continue

        # 2) fuzzy snap (Levenshtein, threshold edit distance)
        best = process.extractOne(
            normalized,
            pool,
            scorer=fuzz.ratio,
            score_cutoff=70,  # quick filter; we'll refine with distance check
        )
        if best:
            candidate, score, _ = best
            distance = Levenshtein.distance(normalized, candidate)
            if distance <= args.threshold:
                sid = variant_to_id[candidate]
                translit = index[sid].get("translit")
                if not args.dry_run:
                    with con:
                        con.execute(
                            "UPDATE entries SET strongs=?, lemma_translit=? WHERE id=?",
                            (sid, translit, entry_id),
                        )
                        # Log the snap in disagreements (transparency)
                        con.execute(
                            """
                            INSERT INTO disagreements (
                                entry_id, field, producer_value, reviewer_value,
                                resolution, resolution_by, resolved_at
                            ) VALUES (?, 'lemma_greek', ?, ?, ?, 'auto:strongs-snap', ?)
                            """,
                            (
                                entry_id,
                                original,
                                f"{candidate} (-> {sid})",
                                f"snapped to {candidate} for {sid}",
                                now,
                            ),
                        )
                fuzzy += 1
                continue

        unmatched += 1

    con.commit()
    con.close()

    print()
    print(f"exact matches:  {exact}")
    print(f"fuzzy snaps:    {fuzzy}")
    print(f"unmatched (G_N/A): {unmatched}")
    print(f"placeholders skipped: {placeholder}")
    print(f"total:          {exact + fuzzy + unmatched + placeholder}")
    if args.dry_run:
        print("(dry-run, no DB writes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
