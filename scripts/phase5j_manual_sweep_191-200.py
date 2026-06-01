"""Phase 5j: one-shot manual sweep of residual disagreements for wave P.

Pages 191-200 (δικαιο- justification cluster -> δόξα/δοῦλος; parsed 2026-06-01).
Mirrors phase5b-i. The cleanest wave so far: audit 95.9% agree+minor, no lemma
errors, no merges/relabels. Phase-3 snap-audit kept δοκίμιος->G1383 (= the NT
neuter δοκίμιον, Jas 1³) and REJECTed διόρθωμα↛διόρυγμα (correction vs trench;
διόρθωμα has no NT ref in the entry and no Strong's of its own -> G_N/A, correct).

phase5_resolve.py auto-closed 11 (7 continuation-notes + 3 has_translation +
1 apostrophe-descriptor). All 5 residuals here are keep_producer:
  d#333/335/336 body: straight vs curly apostrophe in English possessives
    (Peyron's / editor's / Paul's) — typographic only; producer is consistent.
  d#332 δικαιοκρισία papyri: bare "I. 71¹·⁴"/"VI. 904²" are P Oxy anaphora;
    raw-as-written, Phase 4 expands.
  d#344 δολόω papyri: "P Leid X⁷·³⁵"/"xii⁹" split vs reviewer "X⁷·³⁵ and xii⁹"
    merge; both faithful raw forms, Phase 4 normalizes chained refs.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

DECISIONS: dict[int, str] = {
    332: "bare 'I. 71¹·⁴'/'VI. 904²' are P Oxy anaphora; raw-as-written, Phase 4 expands",
    333: "straight vs curly apostrophe in 'Peyron's note'; typographic only, keep producer",
    335: "straight vs curly apostrophe in 'editor's note'; typographic only, keep producer",
    336: "straight vs curly apostrophe in 'Paul's usage'; typographic only, keep producer",
    344: "'P Leid X⁷·³⁵'/'xii⁹' split vs reviewer merge; both faithful raw, Phase 4 normalizes",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = skipped = 0
    with con:
        for did, note in DECISIONS.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1
    print(f"\napplied (keep-producer): {applied}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
