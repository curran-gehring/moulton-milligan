"""Phase 3b: keying corrections for the 561-600 batch (waves BA-BD).

Verified directly against reference/strongs_lemma_index.json.

Bad fuzzy-snaps re-keyed to REAL Strong's:
  id 4044 προεῖπον   G8917->G4280  (suppletive aor. of προερέω; snapped to προσεῖπον
                                    G8917 'address' — wrong word)
  id 4234 ῥέδη       G3976->G4480  (ῥέδα 'chariot' Rev 18:13; snapped to πέδη G3976
                                    'fetter' — wrong word)
  id 4241 ῥήσσω      G20969->G4486 (byform of ῥήγνυμι 'break/dash' Mk 9:18, Lk 9:42;
                                    snapped to extended πήσσω G20969 — wrong word)
  id 4260 ῥυπαίνω    G9007->G4510  (= ῥυπόω 'be filthy' Rev 22:11 WH ῥυπανθήτω; snapped
                                    to ῥαίνω G9007 'sprinkle' — wrong word)

Bad fuzzy-snaps REVERTED to N/A (no genuine NT Strong's lemma; leave strongs NULL so
export renders G_N/A:<lemma> and the coverage gate counts them honestly):
  id 4091 προσαχέω   (snapped προσχέω G8947 — not an NT word; N/A)
  id 4126 προσπαίω   (Mt 7:25 v.l. for προσπίπτω; snapped προσπαίζω G8940 — N/A)
  id 4251 Ῥόδιον     (bracketed ghost/derived form; snapped ῥόδον G21417 — N/A)

NULL rescues (real entries that missed exact-match on the index form):
  id 4019 "Πρίσκα, Πρίσκιλλα" -> G4251 (double-form proper name; key to Πρίσκα G4251;
           Πρίσκιλλα G4252 collapses via dedup)
  id 4032 προβλέπομαι         -> G4265 (mid. of προβλέπω 'foresee/provide' Heb 11:40)
  id 4239 "ῥήγνυμι, ῥήσσω"    -> G4486 (double-form headword; ῥήγνυμι G4486)
  id 4283 "Σαλω(ο)μών"        -> G4672 (variant spelling of Σολομών; MM files it under
           the Σαλ- form between σαλπιστής and Σαμάρεια)

LEFT ALONE (handled elsewhere):
  id 4006 πραϋπάθεια     genuine N/A (1 Tim 6:11 WH; no distinct Strong's) — keep NULL
  id 4039 προδηλόω       p569 continuation (merges into p568 πρόδηλος) — moot snap
  id 4058 προοιμάζομαι   p571 continuation (merges into p570 πρόϊμος) — moot NULL
  id 4175 πρωτεῖα        p587 continuation (merges into p586 πρωτεύω) — moot snap

KEPT snaps (legit accent/breathing/orthography/byform variants — confirmed vs index):
  πραγματία->G4230, προερῶ->G4280, πρόϊμος->G4406, προσωπολημπτέω/-ήμπτης/-ημψία->
  G4380/4381/4382 (WH -μπτ-/-μψ-), πρωΐνός->G4407, πύθων->G4436 (cap), πώς->G4458
  (enclitic), ῥαββεί->G4461, ῥαββουνεί->G4462, ῥαχά->G4469, Ῥοῦβος->G4504 (β/φ),
  Σαμοθράκη->G4543 (iota subscript), Σαπφείρα->G4551.
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
    n = 0
    # (id, strongs_or_None, note, is_snap)
    fixes = [
        (4044, "G4280", "προεῖπον suppletive aor. of προερέω; bad snap προσεῖπον G8917", True),
        (4234, "G4480", "ῥέδα 'chariot' Rev 18:13; bad snap πέδη G3976", True),
        (4241, "G4486", "ῥήσσω byform of ῥήγνυμι Mk 9:18; bad snap πήσσω G20969", True),
        (4260, "G4510", "ῥυπαίνω = ῥυπόω Rev 22:11 (WH); bad snap ῥαίνω G9007", True),
        (4091, None, "προσαχέω: no NT Strong's lemma; revert bad snap προσχέω G8947 -> N/A", True),
        (4126, None, "προσπαίω (Mt 7:25 v.l.): no Strong's; revert bad snap προσπαίζω G8940 -> N/A", True),
        (4251, None, "Ῥόδιον bracketed ghost-form: no Strong's; revert bad snap ῥόδον G21417 -> N/A", True),
        (4019, "G4251", "Πρίσκα, Πρίσκιλλα double-form -> Πρίσκα G4251 (missed exact)", False),
        (4032, "G4265", "προβλέπομαι mid. of προβλέπω Heb 11:40 (missed exact)", False),
        (4239, "G4486", "ῥήγνυμι, ῥήσσω double-form -> ῥήγνυμι G4486 (missed exact)", False),
        (4283, "G4672", "Σαλωμών variant of Σολομών G4672 (MM files under Σαλ-)", False),
    ]
    with con:
        for eid, strongs, note, is_snap in fixes:
            con.execute("UPDATE entries SET strongs=? WHERE id=?", (strongs, eid))
            if is_snap:
                con.execute(
                    """UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                       WHERE entry_id=? AND resolution_by='auto:strongs-snap'""",
                    (note, "manual:strongs-fix", now, eid),
                )
            n += 1
    print(f"applied {n} fixes")
    for eid, *_ in fixes:
        r = con.execute("SELECT id,lemma_greek,strongs FROM entries WHERE id=?", (eid,)).fetchone()
        print(f"  id={r['id']} {r['lemma_greek']} -> {r['strongs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
