"""Phase 5e: one-shot manual sweep of residual disagreements for waves J+K.

Encodes per-case decisions for the disagreements left open by phase5_resolve.py
across pages 131-150 (parsed 2026-06-01). Mirrors phase5b/c/d.

All 11 residuals are keep_producer (citation anaphora = Phase 4 normalization;
the βάτος "(1)/(2)" body markers are MM's faithful homograph disambiguation;
one bracket OCR artifact where the producer is cleaner).

PLUS one homograph re-key uncovered during review (NOT a disagreement row):
entry βάτος (2) — the Hebrew dry-measure (Lk 16:6) — was keyed G0942 (the bush)
because phase3 exact-match picks the lowest-numbered ID when a lemma collides.
Re-keyed to G0943. This also prevents a Phase-6 primary-key collision
((strongs, lemma_greek) would have been (G0942, βάτος) twice -> one row dropped).

Kinds: "keep_producer", "keep_producer_flagged".
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"
INDEX_PATH = ROOT / "reference" / "strongs_lemma_index.json"

DECISIONS: dict[int, tuple] = {
    # citation anaphora / prefix-expansion = Phase 4 normalization (raw-as-written)
    214: ("keep_producer", "bare 763¹⁹ etc. are *OGIS* anaphora; Phase 4 expands"),
    215: ("keep_producer", "P Oxy / ib. anaphora under-resolved; Phase 4 normalizes"),
    217: ("keep_producer", "reviewer rewrites Audollent tablet refs as prose annotation; keep raw"),
    218: ("keep_producer", "bare 33¹/248⁵/90 are *OGIS* anaphora (Rosetta=OGIS 90); Phase 4 expands"),
    220: ("keep_producer", "P Petr/Chrest anaphora + reviewer prose ('Com…'); keep raw-as-written"),
    230: ("keep_producer", "bare 1148⁵/1152²⁴ are BGU IV anaphora; Phase 4 expands"),
    237: ("keep_producer", "bare 50¹⁸ is P Flor I anaphora; Phase 4 expands"),
    239: ("keep_producer", "P Tebt/Chrest anaphora; raw-as-written; Phase 4"),
    # βάτος homographs: '(1)'/'(2)' bold markers are MM's disambiguation, faithful
    # to source; entries are distinguished by distinct Strong's keys (G0942/G0943).
    223: ("keep_producer", "'**βάτος (1)**' marker is MM's homograph label (bush, G0942); faithful to source"),
    224: ("keep_producer", "'**βάτος (2)**' marker is MM's homograph label (measure, re-keyed G0943); faithful"),
    # bracket OCR artifact
    226: ("keep_producer", "source '2 Macc]' has a stray bracket; producer '2 Macc 14⁴²' is cleaner"),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    skipped_already_resolved = 0

    with con:
        for did, decision in DECISIONS.items():
            row = con.execute(
                "SELECT entry_id, resolution FROM disagreements WHERE id=?", (did,)
            ).fetchone()
            if not row:
                print(f"  d#{did}: not found, skip")
                continue
            if row["resolution"] is not None:
                skipped_already_resolved += 1
                continue
            kind = decision[0]
            if kind == "keep_producer":
                resolution, resolution_by = decision[1], "manual:keep-producer"
            elif kind == "keep_producer_flagged":
                resolution, resolution_by = decision[1], "manual:keep-producer-flagged"
                con.execute("UPDATE entries SET needs_review=1 WHERE id=?", (row["entry_id"],))
            else:
                print(f"  d#{did}: unknown kind {kind!r}; skip")
                continue
            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                "WHERE id=? AND resolution IS NULL",
                (resolution, resolution_by, now, did),
            )
            applied += 1

        # --- homograph re-key (not tied to a disagreement row) ---
        idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        translit = idx["G0943"].get("translit")
        e = con.execute(
            "SELECT id, strongs FROM entries WHERE page_no=137 AND lemma_greek='βάτος' "
            "AND body_markdown LIKE '%(2)%'"
        ).fetchone()
        rekeyed = 0
        if e and e["strongs"] != "G0943":
            con.execute(
                "UPDATE entries SET strongs='G0943', lemma_translit=? WHERE id=?",
                (translit, e["id"]),
            )
            con.execute(
                """INSERT INTO disagreements
                   (entry_id, field, producer_value, reviewer_value,
                    resolution, resolution_by, resolved_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (e["id"], "strongs", "G0942 (phase3 lowest-id collision pick)", "G0943 βάτος",
                 "homograph re-key: βάτος (2) is the Hebrew dry-measure (Lk 16:6)=G0943, not the "
                 "bush G0942; also prevents (strongs,lemma) PK collision in Phase 6",
                 "manual:strongs-fix", now),
            )
            rekeyed = 1

    print(f"\napplied (disagreements): {applied}")
    print(f"homograph re-keys:       {rekeyed} (βάτος(2)->G0943)")
    print(f"skipped already-resolved: {skipped_already_resolved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
