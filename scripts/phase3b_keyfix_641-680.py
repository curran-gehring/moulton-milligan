"""Phase 3b: keying corrections for the 641-680 batch (Σ-tail -> Τ -> Υ).

Verified vs reference/strongs_lemma_index.json + page bodies. Most of the 36 snaps
were the legit συν->συμ (before π/φ) / συν->συσ (before σ) assimilation to the NT
form (συνπάσχω->συμπάσχω G4841, συνστέλλω->συστέλλω G4958, etc.) — KEPT untouched.

BAD SNAPS re-keyed to the REAL Strong's (wrong-word coincidental snaps):
  id 4677 συνπορεύομαι G9306->G4848 (συμπορεύομαι 'go with' Lk 7:11; snapped συνεκπορεύομαι)
  id 4704 συνχαίρω     G4868->G4796 (συγχαίρω 'rejoice with' Lk 1:58; snapped συναίρω
                                     'settle accounts' — wrong word)
  id 4864 τολμηρῶς     G5113->G5112 (adv, Rom 15:15 τολμηρότερον; snapped to the noun
                                     τολμητής G5113 2 Pet 2:10 — wrong word)

NULL rescues (real NT words / forms that missed exact match on the index lemma form):
  id 4707 συνχύννω      -> G4797 (Hellenistic form of συγχέω, Ac 2:6/21:31; body says so)
  id 4779 "τάχε(ι)ον"   -> G5032 (τάχιον, Jn 13:27/20:4/Heb 13:19,23; MM cross-refs it
                                  's.v. ταχέως' but it is a real NT lemma — key for reach)
  id 4851 "τίς, τί"     -> G5101 (interrog. pron.; double-form headword)
  id 4877 "τραπεζ(ε)ίτης"-> G5133 (money-changer, Mt 25:27; (ε) spelling-variant marker)

RELABEL (OCR capitalized an enclitic particle as a headword):
  id 4785 "ΤΕ" -> τε G5037 (the enclitic particle τε 'and'; body 'For this enclitic
                            particle cf. ...')

N/A tombstone (prefix cross-ref stub, protect from re-snap):
  id 4679 συνσο— ('See passim συσσο—')

LEFT FOR PHASE 5 (continuation fragment — merges into prior-page entry):
  id 4682 σύνστοιχος (p643 pos1; tail of p642 συστοιχέω, Gal 4:25 discussion)
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()

    # (id, new_lemma_or_None, strongs_or_None, note, had_snap)
    fixes = [
        (4677, None, "G4848", "συμπορεύομαι Lk 7:11; bad snap συνεκπορεύομαι G9306", True),
        (4704, None, "G4796", "συγχαίρω Lk 1:58; bad snap συναίρω G4868", True),
        (4864, None, "G5112", "τολμηρῶς adv Rom 15:15; bad snap τολμητής G5113", True),
        (4707, None, "G4797", "συνχύννω = συγχέω Ac 2:6 (Hellenistic form) — rescue", False),
        (4779, None, "G5032", "τάχε(ι)ον = τάχιον Jn 13:27 (MM x-refs s.v. ταχέως) — rescue", False),
        (4851, None, "G5101", "τίς, τί interrog. pron. (double-form) — rescue", False),
        (4877, None, "G5133", "τραπεζ(ε)ίτης money-changer Mt 25:27 — rescue", False),
        (4785, "τε", "G5037", "OCR ΤΕ -> enclitic particle τε — relabel + key", False),
        (4679, None, None, "συνσο— prefix cross-ref stub -> N/A", False),
    ]

    with con:
        for eid, new_lemma, strongs, note, had_snap in fixes:
            row = con.execute("SELECT lemma_greek FROM entries WHERE id=?", (eid,)).fetchone()
            if row is None:
                print(f"  WARN id={eid} not found"); continue
            old_lemma = row["lemma_greek"]
            if new_lemma is not None:
                con.execute("UPDATE entries SET lemma_greek=?, strongs=? WHERE id=?",
                            (new_lemma, strongs, eid))
            else:
                con.execute("UPDATE entries SET strongs=? WHERE id=?", (strongs, eid))
            if had_snap:
                con.execute(
                    """UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                       WHERE entry_id=? AND resolution_by='auto:strongs-snap'""",
                    (note, "manual:strongs-fix", now, eid))
            if strongs is None:
                has = con.execute(
                    """SELECT 1 FROM disagreements WHERE entry_id=?
                       AND resolution_by='manual:strongs-fix' AND reviewer_value='G_N/A'""",
                    (eid,)).fetchone()
                if not has:
                    con.execute(
                        """INSERT INTO disagreements
                           (entry_id, field, producer_value, reviewer_value,
                            resolution, resolution_by, resolved_at)
                           VALUES (?,?,?,?,?,?,?)""",
                        (eid, "strongs", old_lemma, "G_N/A", note,
                         "manual:strongs-fix", now))
            if new_lemma is not None and new_lemma != old_lemma:
                con.execute(
                    """INSERT INTO disagreements
                       (entry_id, field, producer_value, reviewer_value,
                        resolution, resolution_by, resolved_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (eid, "lemma_greek", old_lemma, new_lemma, note,
                     "manual:lemma-swap", now))

    print(f"applied {len(fixes)} keyfix decisions")
    for eid, *_ in fixes:
        r = con.execute("SELECT id,lemma_greek,strongs FROM entries WHERE id=?", (eid,)).fetchone()
        if r:
            print(f"  id={r['id']:5d} {r['lemma_greek']:22s} -> {r['strongs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
