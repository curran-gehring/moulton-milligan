"""Phase 5c: one-shot sweep of the residual manual disagreements for waves E-G.

NOT a reusable resolver — it encodes per-case decisions made during a manual
review of the 20 disagreements left open by phase5_resolve.py across pages
81-110 (parsed 2026-06-01). Mirrors phase5b_manual_sweep.py's structure.

Decision kinds:
- "lemma_swap"        — change lemma_greek + clear strongs+translit (phase3 re-keys)
- "set_nt_references" — overwrite entries.nt_references with given JSON list string
- "keep_producer"     — close-only, no entry mutation
- "keep_producer_flagged" — keep producer + assert needs_review=1

Guiding precedent (from spec + phase5b): citation prefix-expansion, ib./id.
anaphora resolution, and bare-superscript line-refs are PHASE 4 normalization
work — keep the producer's raw-as-written value and let Phase 4 normalize.
Discretionary/line-break hyphens that the parser correctly removed are kept
(producer is more correct). Only genuine Phase-2 errors (wrong continuation
lemma, a real missed NT reference attested verbatim in the body) get mutated.

After running, follow with:
  python scripts/phase3_strongs.py --from 81 --to 110   # re-keys swapped lemmas
  python scripts/phase6_export.py                       # (when exporting)

Idempotent — only touches rows where `resolution IS NULL`.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

DECISIONS: dict[int, tuple] = {
    # --- reviewer-wins (real Phase-2 corrections) ---
    140: ("lemma_swap", "ἀπόδειξις",
          "p91 opens mid-entry; page 90 ends with ἀπόδειξις cut off (not ἀποδείκνυμι). "
          "Body discusses noun senses proofs/election/display = ἀπόδειξις."),
    145: ("lemma_swap", "ἀποκρίνομαι",
          "p95 ?? continuation tail; page 94 ends with ἀποκρίνομαι cut off. "
          "Reviewer + cross-page continuation both confirm ἀποκρίνομαι."),
    166: ("set_nt_references", '["Phil 2⁶", "Mk 10⁴¹"]',
          "p108 ἁρπαγμός body reads 'οὐκ ἐστὶν ἁρπαγμὸς ἡ τιμή (from a catena on Mk 10⁴¹)' "
          "— a real NT ref using the headword; parser missed it. Verified against page-108 source."),

    # --- keep-producer: citation shorthand/anaphora = Phase 4 normalization (raw-as-written) ---
    121: ("keep_producer_flagged",
          "mostly Phase-4 normalization (*id.*->BGU, *Syll* prefix on 587/588/611 anaphora). "
          "Reviewer also drops a boundary-leaked 'P Petr III. 11' from the next entry + reads "
          "'Magnesian inscriptions 83' — flag for the Phase-4 citation-boundary pass; keep raw now."),
    122: ("keep_producer", "separator ;->, and trailing ⁴⁹ anaphoric line-ref; raw-as-written"),
    124: ("keep_producer", "reviewer expands bare ¹⁴² -> *ib*. 737¹⁴² (anaphora); Phase 4 normalizes"),
    131: ("keep_producer", "reviewer adds missing close-paren on (A.D. 147); cosmetic, date intact"),
    132: ("keep_producer", "bare ¹⁰⁰ is anaphoric line-ref for preceding P Ryl I. 28; preserve per spec"),
    133: ("keep_producer", "bare 850 (ii/B.C.) is *Syll* anaphora; Phase 4 expands (cf. phase5b d#95)"),
    135: ("keep_producer", "reviewer restores parenthetical annotation (—see above…)(= III. p. 126); "
                           "core citation P Lond 904⁴⁰ (A.D. 104) intact; raw-as-written"),
    147: ("keep_producer", "Fⁱⁱⁱ·⁸⁸ / ⁱ·¹⁸ are anaphoric subrefs of P Leid W; Phase 4 groups them"),
    153: ("keep_producer", "bare 54⁷⁵ / 256 are P Fay anaphora carryover; Phase 4 expands"),
    154: ("keep_producer_flagged",
          "reviewer expands ib./X. P Oxy anaphora (Phase 4) AND flags two omitted line-refs "
          "(275³⁸, 496¹⁵, 37ⁱⁱ·¹). The omissions need a re-extraction, not normalization — flag."),
    162: ("keep_producer", "bare 22¹³ is P Giss anaphora carryover; Phase 4 expands"),
    163: ("keep_producer", "reviewer adds bare 'ί Pet'/'2 Pet' book mentions w/o verse — not citations; "
                           "keep producer's specific 2 Pet 1³ (cf. phase5b d#99)"),

    # --- keep-producer: discretionary/line-break hyphens the parser correctly removed ---
    128: ("keep_producer", "discretionary hyphen in 'unfortunately' correctly normalized; producer cleaner"),
    129: ("keep_producer", "discretionary hyphen in 'vernacular' correctly normalized; producer cleaner"),
    130: ("keep_producer", "discretionary hyphens in 'concerning'/'Reference' correctly normalized"),
    148: ("keep_producer", "line-break hyphen in author name 'West-cott' correctly removed"),
    149: ("keep_producer", "line-break hyphen in 'Anto-nines' correctly removed"),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    entry_mutations = 0
    skipped_already_resolved = 0

    with con:
        for did, decision in DECISIONS.items():
            row = con.execute(
                "SELECT entry_id, field, resolution FROM disagreements WHERE id=?",
                (did,),
            ).fetchone()
            if not row:
                print(f"  d#{did}: not found, skip")
                continue
            if row["resolution"] is not None:
                skipped_already_resolved += 1
                continue
            entry_id = row["entry_id"]
            kind = decision[0]

            if kind == "lemma_swap":
                new_lemma, reason = decision[1], decision[2]
                con.execute(
                    "UPDATE entries SET lemma_greek=?, strongs=NULL, lemma_translit=NULL WHERE id=?",
                    (new_lemma, entry_id),
                )
                # The lemma changed, so any prior "leave unkeyed" tombstone for the
                # OLD lemma no longer applies — clear it so phase3 can key the new lemma.
                con.execute(
                    "DELETE FROM disagreements WHERE entry_id=? "
                    "AND resolution_by='manual:strongs-fix' AND reviewer_value='G_N/A'",
                    (entry_id,),
                )
                resolution = f"lemma swapped to {new_lemma!r}; strongs cleared for re-keying. {reason}"
                resolution_by = "manual:lemma-swap"
                entry_mutations += 1

            elif kind == "set_nt_references":
                new_refs_json, reason = decision[1], decision[2]
                con.execute(
                    "UPDATE entries SET nt_references=? WHERE id=?",
                    (new_refs_json, entry_id),
                )
                resolution = f"nt_references set to {new_refs_json}. {reason}"
                resolution_by = "manual:nt-refs-fix"
                entry_mutations += 1

            elif kind == "keep_producer":
                resolution = decision[1]
                resolution_by = "manual:keep-producer"

            elif kind == "keep_producer_flagged":
                resolution = decision[1]
                resolution_by = "manual:keep-producer-flagged"
                con.execute("UPDATE entries SET needs_review=1 WHERE id=?", (entry_id,))

            else:
                print(f"  d#{did}: unknown decision kind {kind!r}; skipping")
                continue

            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                "WHERE id=? AND resolution IS NULL",
                (resolution, resolution_by, now, did),
            )
            applied += 1

    print(f"\napplied:                  {applied}")
    print(f"entry mutations:          {entry_mutations}")
    print(f"skipped already-resolved: {skipped_already_resolved}")
    print(f"\nNext: python scripts/phase3_strongs.py --from 81 --to 110")
    return 0


if __name__ == "__main__":
    sys.exit(main())
