"""Phase 5n: one-shot manual sweep of residual disagreements for wave T.

Pages 231-240 (ἐλ-/ἐμ-/ἐν- section, incl. the function-word ἐν spanning 239-240).
Mirrors phase5b-m. Phase-2 audit 89.3% agree+minor (above gate). phase5_resolve.py
auto-closed 7 (6 continuation-note acceptances + 1 has-translation-from-body for
ἐμπαιγμός). This script handles the residual 8.

Phase-3 keying: 71 exact + 2 fuzzy snaps (BOTH Codex-audited KEEP: ἐλλογάω->G1677
-άω/-έω byform; ἐμπί(μ)πλημι->G1705 μ-variant) + 2 unmatched. The 2 unmatched were
manually resolved during Phase 3:
  - ἐμπί(μ)πρημι, ἐμπρήθω (p237) -> G1714 (positive key; ἐμπρήθω byform = Mt 22:7
    ἐνέπρησεν; classic id chosen over extended G7196 ἐμπίμπρημι).
  - ἐμμέσῳ (p236) -> G_N/A (crasis variant of ἐν μέσῳ, Rev 1:13 v.l. AC; no own Strong).

Homograph pass: NO Wave-T entry is a homograph. The pass surfaced prior-wave εἰ
entries (p211/p212, wave R, never homograph-swept) where Codex Tier-2 wrongly proposed
εἰ(G1487)->εἰ μή(G1508) on the entry HEAD (id 1397) while keeping its own continuation
tail (id 1398) as G1487 — self-inconsistent. The p211 entry is the general conditional
particle εἰ ("weakening of the distinction between εἰ and ἐάν...use of εἰ with the
subjunctive"); the εἰ μή in the body is an illustrative example. Pre-settled BOTH εἰ
entries to G1487 before the apply-run so the homograph pass skipped them.

adopt_reviewer (1):
  d#433 ἐλεεινός: producer over-fragmented "P Oxy I. 130²², ⁷, ²⁰" into detached
    superscripts ["⁷","²⁰"]; reviewer correctly reads them as P Oxy I. 130 lines 7,20.
    These are parse artifacts, not anaphoric shorthand — adopt reviewer's reconstruction.

keep_producer (7):
  d#434 ἐλεέω / d#436 ἐλλογάω: variant marker '(—άω)'/'(—έω)' — clean lemma kept
    (correct for keying: ἐλεέω G1656, ἐλλογάω->G1677), marker stays in body (wave-S convention)
  d#437 ἐλλογάω body: producer keeps the '(—έω).' variant marker at body head; legit MM
    content documenting the -έω byform; reviewer dropped it — keep producer
  d#439 ἐμμέσῳ: iota-subscript ἐμμέσῳ is the dative of ἐν μέσῳ (correct); reviewer's
    'ἐμμέσω' drops the subscript — keep producer (entry is G_N/A regardless)
  d#442 ἐμπί(μ)πλημι: '*Syll* 803⁵⁷ (iii/B.C.); 127' grouping vs reviewer's
    '803⁵⁷, 127 (iii/B.C.)' — trivial date-grouping, Phase 4 normalizes
  d#443 ἐμπλοκή: producer 'P Ryl II. 124²³' clean; reviewer '124⁲³' uses a stray
    U+2072 glyph — keep producer
  d#445 ἐν: standalone '⁴¹' is line-41 anaphora of *ib.* 5; raw-as-written, Phase 4
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

KEEP: dict[int, str] = {
    434: "variant marker '(—άω)' belongs in body; clean lemma ἐλεέω keys G1653",
    436: "variant marker '(—έω)' belongs in body; clean lemma ἐλλογάω keys G1677 (-έω byform)",
    437: "producer keeps '(—έω).' variant marker at body head — legit MM content; keep producer",
    439: "ἐμμέσῳ iota-subscript is correct (dative of ἐν μέσῳ); reviewer drops subscript — keep producer (G_N/A anyway)",
    442: "'*Syll* 803⁵⁷ (iii/B.C.); 127' vs reviewer date-grouping; trivial, Phase 4 normalizes",
    443: "producer 'P Ryl II. 124²³' clean; reviewer '124⁲³' uses stray U+2072 glyph — keep producer",
    445: "standalone '⁴¹' = line-41 anaphora of *ib.* 5; raw-as-written, Phase 4 normalizes",
}

# d#433: adopt reviewer's reconstructed citation list (entry 1548 ἐλεεινός)
ADOPT = {433: 1548}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = adopted = skipped = 0

    with con:
        # ---- keep-producer residuals ----
        for did, note in KEEP.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

        # ---- adopt-reviewer: d#433 ἐλεεινός citation reconstruction ----
        for did, eid in ADOPT.items():
            row = con.execute("SELECT resolution, reviewer_value FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            new_cits = json.loads(row["reviewer_value"])  # validated to parse earlier
            con.execute("UPDATE entries SET papyri_citations=? WHERE id=?",
                        (json.dumps(new_cits, ensure_ascii=False), eid))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL",
                        ("producer over-fragmented P Oxy I. 130 lines into detached superscripts ['⁷','²⁰']; "
                         "adopted reviewer's reconstruction (P Oxy I. 130⁷, 130²⁰)",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

    print(f"\napplied (keep-producer): {applied}")
    print(f"applied (adopt-reviewer): {adopted}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
