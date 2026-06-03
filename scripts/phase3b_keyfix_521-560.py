"""Phase 3b: keying corrections for the 521-560 batch (waves AW-AZ).

Verified directly against reference/strongs_lemma_index.json (base-lemma reverse lookup).

Bad fuzzy-snap re-keyed:
  id 3925 ποία   G21072->G4169  (ποία fem of ποῖος, Jas 4:14; snapped to πτοία
                                 'terror' G21072 — wrong word. MM glosses it 'grass'
                                 but the NT slot Jas 4:14 is tagged ποῖος; dedup
                                 longest-body-wins handles the ποῖος collision.)

G_N/A / NULL rescues (surviving real entries that missed exact-match on index form):
  id 3694 "παριστάνω, παρίστημι" -> G3936 (the παρίστημι HEAD on p524; trans. sense
           'place beside/present'; id 3695 is the p525 continuation, merged in phase5)
  id 3707 παροξύνομαι           -> G3947 (παροξύνω 'provoke', 1 Cor 13:5)
  id 3781 περιβλέπομαι          -> G4017 (περιβλέπω 'look round', Mk 3:5; real entry —
           p535 pos1 περιβάλλω is the continuation, this pos2 is the genuine entry)
  id 3862 Πισίδιος             -> G4099 (Πισιδία; adj. for Pisidian Antioch Ac 13:14 WH)
  id 3909 "πλόος, πλοῦς"        -> G4144 (πλόος 'voyage', Ac 27:9; double-form lemma)

KEEP snaps (legit accent/breathing/spelling/byform variants — confirmed by index):
  παρεισδύω->G3921 (-ω/-νω), Πατρόβας->G3969 (accent), πατρολῴας->G3964 (α/ο variant),
  Πειλᾶτος->G4091 x2 (ει/ι), Πέργαμον->G4010 (-ον/-ος), περιρήγνυμι->G4048 (ρ/ρρ),
  Πέρσις->G4069 (accent), πιθός->G3981 (ει/ι πειθός), πλημμύρα->G4132 (accent).
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
    fixes = [
        (3925, "G4169", "ποία fem of ποῖος Jas 4:14; wrong snap to πτοία G21072", True),
        (3694, "G3936", "παρίστημι head (trans. 'present'); double-form lemma missed exact", False),
        (3707, "G3947", "παροξύνω 'provoke' 1 Cor 13:5; middle form missed exact", False),
        (3781, "G4017", "περιβλέπω 'look round' Mk 3:5; middle form missed exact", False),
        (3862, "G4099", "Πισιδία; adj Πισίδιος Ac 13:14 WH reachability", False),
        (3909, "G4144", "πλόος 'voyage' Ac 27:9; double-form lemma missed exact", False),
    ]
    with con:
        for eid, strongs, note, is_snap in fixes:
            con.execute("UPDATE entries SET strongs=? WHERE id=?", (strongs, eid))
            if is_snap:
                con.execute(
                    """UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                       WHERE entry_id=? AND resolution_by='auto:strongs-snap' AND resolution IS NULL""",
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
