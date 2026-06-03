"""Phase 3b: keying corrections for the 681-720 batch (Υ-tail -> Φ -> Χ).

Verified vs reference/strongs_lemma_index.json + page bodies. Very clean batch —
only 12 snaps, mostly legit spelling-variant keeps (accent / ε-ει / single-double
consonant / ν-νν): ὑπερεκχύνω G5240, φαρμακεία G5331, φαρμακος G5333, φιλονεικία
G5379, φόβητρον G5400, Φύγελλος G5436, Χανααναῖος G5478, χερουβίμ G5502, Φόρον
G5410 (Appii Forum, Ac 28:15) — all KEPT.

BAD SNAPS re-keyed:
  id 5108 Φιλαδελφία  G5360->G5359 (the CITY Rev 1:11/3:7 = Φιλαδέλφεια G5359; snapped
                                    to the common noun φιλαδελφία 'brotherly love' G5360
                                    — the next, separate entry)
  id 5242 χειρίζω     G7039->N/A   (non-NT papyri verb 'manage'; snapped to ἐγχειρίζω
                                    extended G7039; p717 pos-1 continuation fragment —
                                    Phase 5 will merge it; revert key meanwhile)

NULL rescues (real NT words missed on index lemma form):
  id 4979 ὑπερεῖδον   -> G5237 (ὑπερείδω 'overlook', Ac 17:30 ὑπεριδών)
  id 5039 ὑποστρωννύω -> G5291 (ὑποστρώννυμι 'spread underneath', Lk 19:36)
  id 5148 φοβέομαι    -> G5399 (φοβέω; mid/pass deponent, ubiquitous in NT)

N/A tombstones (non-NT / variant-readings / cross-ref stubs):
  id 4984 ὑπερευχαριστέω (body: 'not a NT word')
  id 5020 ὑπολαμπάς     (Ac 20:8 D-reading variant for λαμπάς; no own Strong's)
  id 5094 φημίζω        (Mt 28:15 v.l. for διαφημίζω; no distinct Strong's)
  id 5153 Φοινίκισσα    (cross-ref stub 'See s.v. Συροφοινίκισσα')
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

    fixes = [
        (5108, "G5359", "Φιλαδελφία the CITY Rev 1:11; bad snap to φιλαδελφία 'love' G5360", True),
        (5242, None, "χειρίζω non-NT; revert bad snap ἐγχειρίζω G7039 -> N/A", True),
        (4979, "G5237", "ὑπερεῖδον = ὑπερείδω Ac 17:30 — rescue", False),
        (5039, "G5291", "ὑποστρωννύω = ὑποστρώννυμι Lk 19:36 — rescue", False),
        (5148, "G5399", "φοβέομαι = φοβέω (mid/pass deponent) — rescue", False),
        (4984, None, "ὑπερευχαριστέω 'not a NT word' -> N/A", False),
        (5020, None, "ὑπολαμπάς Ac 20:8 D-variant; no Strong's -> N/A", False),
        (5094, None, "φημίζω Mt 28:15 v.l. for διαφημίζω; no distinct Strong's -> N/A", False),
        (5153, None, "Φοινίκισσα cross-ref stub 'See s.v. Συροφοινίκισσα' -> N/A", False),
    ]

    with con:
        for eid, strongs, note, had_snap in fixes:
            row = con.execute("SELECT lemma_greek FROM entries WHERE id=?", (eid,)).fetchone()
            if row is None:
                print(f"  WARN id={eid} not found"); continue
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
                        (eid, "strongs", row["lemma_greek"], "G_N/A", note,
                         "manual:strongs-fix", now))

    print(f"applied {len(fixes)} keyfix decisions")
    for eid, *_ in fixes:
        r = con.execute("SELECT id,lemma_greek,strongs FROM entries WHERE id=?", (eid,)).fetchone()
        if r:
            print(f"  id={r['id']:5d} {r['lemma_greek']:20s} -> {r['strongs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
