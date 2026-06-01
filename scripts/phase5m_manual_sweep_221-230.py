"""Phase 5m: one-shot manual sweep of residual disagreements for wave S.

Pages 221-230 (dense ἐκ- compounds). Mirrors phase5b-l. Audit 84.3% — marginally
below the 85% gate, NON-systemic (lesson #1: no prompt-refine). The dip is driven by
a variant-marker convention this wave: 4 entries (ἑκατοντάρχης, ἐκγαμίζω, ἐκκοπή,
ἐκκόπτω) print a parenthetical spelling variant after the headword; the producer
keeps the CLEAN lemma (correct for keying — all keyed exactly: G1543/G1547/.../G1581)
and puts the marker in the body, the reviewer wants it folded into the lemma. Keep
producer (8 disagreements). Plus a p229 stretch where the reviewer over-eagerly
adds refs.

Phase-3 snap-audit REJECTed 2 (both -> G_N/A, correct): ἐκκοπή↛ἐγκοπή (the noun
ἐκκοπή isn't NT; ἐγκοπή G1464 is the wrong prefix) and ἔκτρομος↛ἔντρομος (Heb 12:21
ἐκ- variant of ἔντρομος, no own Strong's). No manual positive keying needed.

⚠️ auto:reviewer-superset-citations OVER-APPLIED on d#424 (ἐκτρέπω): it added the
CLASSICAL AUTHORS "Epict. i. 6. 42" and "Musonius p. 26⁴" to papyri_citations. Per
the established convention, documentary papyri + epigraphic series (OGIS, Syll,
Calder, Waddington, JHS, Oenoanda, Hadrumetum inscr.) belong in citations, but
classical/literary AUTHORS (Epictetus, Musonius, Menander-author, etc.) belong in the
BODY. Reverted those two from ἐκτρέπω; the other superset adds this wave (d#423
Waddington/JHS, d#425 Calder, d#426 Hadrumetum inscr., d#427 P Ryl) are legit
epigraphic/papyri and were left as the policy applied them.

keep_producer (all 14 residuals):
  d#404/405 ἑκατοντάρχης, d#406/407 ἐκγαμίζω, d#414/415 ἐκκοπή, d#416/417 ἐκκόπτω:
    variant marker '(—ος)'/'(ἐνκοπή)'/'(ἐνκόπτω)' — clean lemma kept, marker in body
  d#408 ἐκδίκησις / d#409 ἐκδύω: mid-body capital breathing/accent (Ἔκδικία, ἀρθὸν);
    cosmetic, Phase 4 proofs
  d#411 ἐκκλησία: curly apostrophe "Christ's"
  d#419 ἔκπαλαι: reviewer transliterated 'Ἔκτοτε'->'Ektote' (WRONG, keep Greek)
  d#420 ἐκπληρόω: chained 'BGU IV. 1053...; 1055⁶' raw; Phase 4
  d#422 ἐκτίθημι: reviewer's 'Ac 7¹⁹' is NOT in the body (the entry's ἔκθετα is the
    cognate ἔκθετος verse, not an ἐκτίθημι ref); producer correct
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
    404: "variant marker '(—ος)' belongs in body; clean lemma ἑκατοντάρχης keys G1543",
    405: "'(—ος)' 2nd-decl variant note is MM content; keep in body",
    406: "variant marker '—ίσκω' belongs in body; clean lemma ἐκγαμίζω keys G1547",
    407: "'—ίσκω' (ἐκγαμίσκω) variant note is MM content; keep in body",
    408: "mid-body capital breathing 'Ἔκδικία' vs 'Ἐκδικία'; cosmetic, Phase 4 proofs",
    409: "mid-body OCR 'ἀρθὸν'/'ὀρθὸν' + breathing; cosmetic, Phase 4 proofs",
    411: "curly vs straight apostrophe in \"Christ's\"; typographic only",
    414: "variant marker '(ἐνκοπή)' belongs in body; clean lemma ἐκκοπή (now G_N/A)",
    415: "'(ἐνκοπή)' spelling-variant note is MM content; keep in body",
    416: "variant marker '(ἐνκόπτω)' belongs in body; clean lemma ἐκκόπτω keys G1581",
    417: "'(ἐνκόπτω)' note + 'Milligan's' apostrophe; keep producer",
    419: "reviewer transliterated Greek 'Ἔκτοτε'->'Ektote' (wrong); keep Greek",
    420: "chained 'BGU IV. 1053...; 1055⁶' raw-as-written; Phase 4 normalizes",
    422: "reviewer 'Ac 7¹⁹' not in body; entry's ἔκθετα is cognate ἔκθετος (Ac 7:19), not an ἐκτίθημι ref; producer correct",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = skipped = 0

    with con:
        for did, note in KEEP.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

        # ---- d#424 revert: drop the two classical-author refs from ἐκτρέπω papyri ----
        reverted = 0
        e = con.execute("SELECT papyri_citations FROM entries WHERE id=1521").fetchone()
        if e:
            arr = json.loads(e["papyri_citations"])
            classical = {"Epict. i. 6. 42", "Musonius p. 26⁴"}
            new = [c for c in arr if c not in classical]
            if new != arr:
                con.execute("UPDATE entries SET papyri_citations=? WHERE id=1521",
                            (json.dumps(new, ensure_ascii=False),))
                reverted = 1
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=424",
                        ("auto-superset wrongly added classical authors Epict./Musonius to papyri; reverted — classical authors belong in body, not citations",
                         "manual:keep-producer", now))

    print(f"\napplied (keep-producer): {applied}")
    print(f"ἐκτρέπω classical-author revert: {reverted}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
