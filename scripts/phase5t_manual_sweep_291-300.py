"""Phase 5t: one-shot manual sweep of residual disagreements for wave Z.

Pages 291-300 (εὐ- compounds → ἐχθρός/ἔχω/ἕως — the END of the Ε section). Mirrors
phase5b-s. Phase-2 audit 85.2% agree+minor (just above gate). phase5_resolve.py
auto-closed 14 (6 continuation + 2 has-translation + 6 producer-superset citation
keeps — the p293 cluster, where the reviewer wanted to DROP legit epigraphic refs
OGIS/CIG/Syll/Preisigke that the producer correctly kept). This script handles the
residual 5, all keep-producer.

Phase-3 keying: 79 exact + 1 snap + 1 unmatched + 1 relabel. No snap-audit (the only
snap was a bad snap fixed pre-audit: εὔκοπος→G20477 εὔοπτος WRONG → G2123, Mt 9:5).
No homographs. Unmatched: Εὐρακύλων→G2148 (WH reading at Ac 27:14; index has the TR
form Εὐροκλύδων G2148 — same verse slot, key for reachability). Relabel: id 2072
εὐώδης→εὐωδία G2175 (continuation of p298 εὐωδία; body completes the 'hundred sweet-
smelling jars' transl. + adds εὐώδη papyri; parser took the adj from the quotes — the
continuation-note disagreement d#610 auto-resolved separately).
Note: the two p292 εὐθύς entries (adj + adv senses) both correctly key G2117 (not a
homograph in the index); Phase-6 longest-body-wins dedups them.

keep_producer (5):
  d#606 εὐσέβεια: producer tentatively reconstructed a garbled OCR citation as
    'Preisigke 459⁹'; reviewer disputes (the page has a garbled 'τελεὶ 459⁹'). Keep
    producer's best-guess for Phase-4 image verification — don't assert a different wrong ref.
  d#608 εὔχρηστος: 'Phryn. p. 402' vs reviewer 'Lob. Phryn. p. 402' — adds the editor
    Lobeck; but Phrynichus is a classical grammarian ref (belongs in body, not papyri_
    citations); keep producer, Phase 4 relocates.
  d#609 εὐψυχέω: 'Vis. i. iii. 2' vs reviewer 'Hermas Vis. i. iii. 2' — Shepherd of
    Hermas is a patristic text (belongs in body); keep producer.
  d#613 ἔχθρα body / d#614 ἔχθρα citations: producer cleaned the OCR garble 'P Tebt I.
    5�255' → 'P Tebt I. 5²⁵⁵' (correct superscript reconstruction); reviewer keeps the
    replacement-char garble. Keep producer.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

KEEP: dict[int, str] = {
    606: "garbled OCR citation tentatively reconstructed 'Preisigke 459⁹'; reviewer disputes — keep producer's best-guess for Phase-4 image verification",
    608: "'Phryn.' (Phrynichus) is a classical grammarian ref (belongs in body, not papyri_citations); reviewer adds editor 'Lob.'; keep producer, Phase 4 relocates",
    609: "'Hermas Vis.' = Shepherd of Hermas, a patristic text (belongs in body); keep producer",
    613: "producer cleaned OCR garble 'P Tebt I. 5�255' → '5²⁵⁵' (correct superscript reconstruction); keep producer",
    614: "producer cleaned OCR garble 'P Tebt I. 5�255' → '5²⁵⁵'; keep producer",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = skipped = 0

    with con:
        for did, note in KEEP.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

    print(f"\napplied (keep-producer): {applied}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
