"""Phase 3b: keying corrections for the 481-520 batch (waves AS-AV).

Verified directly against reference/strongs_lemma_index.json (base-lemma reverse
lookup — same index the keyer uses).

Bad fuzzy-snaps re-keyed (wrong-stem; promote auto:strongs-snap -> manual:strongs-fix):
  id 3417 ὁπλίζομαι  G0835->G3695  (ὁπλίζω 'arm', 1 Pet 4:1; snapped to αὐλίζομαι)
  id 3490 οὖ/οὗ      G3767->G3757  (οὗ relative adv 'where'; snapped to οὖν G3767)
  id 3527 ὀχετός     G0105->G_N/A  (Mk 7:19 v.l. 'drain', not in index; snapped to ἀετός)

G_N/A / NULL rescues (surviving real entries that missed exact-match on index form):
  id 3434 ὀργίζομαι       -> G3710 (ὀργίζω; the real 'am angry' entry — id 3433 is
           the ὀργή continuation, merged separately in phase5)
  id 3514 "οὕτως, οὕτω"   -> G3779 (οὕτω; double-form lemma)
  id 3616 παρακαθέζομαι   -> G3869 (παρακαθίζω; Lk 10:39 only)
  id 3470 ὅς γε           -> G_N/A (ὅς γε combination, Rom 8:32; no single Strong's)

KEEP snaps (legit breathing/accent/assimilation/dialect variants — confirmed by
index): ὁρκωμοσία->G3728 (breathing), ὄρνιξ->G3733 (Doric of ὄρνις), ὀσφύς->G3751
(accent), πανοικί->G3832, παμπληθεί->G3826, πανταχῆ->G6069, παραπλήσιον->G3897.
Continuation-entry snaps (ὀρκωμοσία#1 3453, οὐδέποτε 3496, οὐχί#1 3515,
παλινγενεσία 3564) are left as-is — phase5 merges them into their prior-page head.
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
        (3417, "G3695", "ὁπλίζω; wrong snap to αὐλίζομαι G0835", True),
        (3490, "G3757", "οὗ relative adv; wrong snap to οὖν G3767", True),
        (3527, "G_N/A", "ὀχετός Mk 7:19 v.l., not in index; wrong snap to ἀετός", True),
        (3434, "G3710", "ὀργίζω 'am angry'; missed exact-match on middle form", False),
        (3514, "G3779", "οὕτω; double-form lemma missed exact-match", False),
        (3616, "G3869", "παρακαθίζω Lk 10:39; missed exact-match", False),
        (3470, "G_N/A", "ὅς γε combination Rom 8:32; no single Strong's", False),
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
