"""Phase 3b: keying corrections for the 441-480 batch (waves AO-AR).

Verified directly against reference/strongs_lemma_index.json (authoritative —
it is the same index the keyer uses; base-lemma reverse lookup confirmed each).

Bad fuzzy-snaps re-keyed (wrong-stem; promote auto:strongs-snap -> manual:strongs-fix):
  id 3105 μητί        G3383->G3385  (μήτι; snapped to μήτε G3383 — wrong word)
  id 3145 μοιχάομαι   G8468->G3429  (μοιχάω; snapped to οἴχομαι G8468 — dropped μ)
  id 3146 μοιχάομαι   G8468->G3429  (second μοιχάομαι entry on p446; same fix)
  id 3220 νεώτερος    G0511->G3501  (νέος comparative; snapped to ἀνώτερος G0511)
  id 3319 οἰκέτεια    G8450->G6064  (οἰκετεία EXACT G6064; snapped to οἰκέτις — accent
                                     diff hid the exact match from phase3)

G_N/A / NULL rescues (real NT words that missed exact-match on the index lemma form,
mostly double-form "X, Y" lemmas or middle-vs-active):
  id 3119 μιμνήσκομαι      -> G3403 (μιμνήσκω; Heb 2:6, 13:3)
  id 3175 "Μύρα, Μύρρα"    -> G3460 (Μύρα; Ac 27:5)
  id 3294 "ὁ, ἡ, τό"       -> G3588 (definite article — first page of the mega-entry)
  id 3295 "ὁ, ἡ, τό"       -> G3588 (article continuation onto p467)
  id 3308 ὀδυνάομαι        -> G3600 (ὀδυνάω; Lk 16:25)
  id 3344 "οἶμαι, οἴομαι"  -> G3633 (οἴομαι; Jn 21:25, Phil 1:17)
  id 3380 "ὄμνυμι, ὀμνύω"  -> G3660 (ὀμνύω; Jas 5:12)
  id 3349 οἱοσδηποτοῦν     -> G_N/A (only in the disputed Lachmann reading of Jn 5:4;
                                     no clean Strong's number — keep sentinel)

KEEP snaps (legit orthographic/breathing/accent variants — confirmed by index reverse
lookup): μῆτις->G3387, μῖγμα, μητραλῴας, μυρίοι, Ναζαρέτ, νουμηνία, νηφάλεος, νεοσσός,
Νυμφας, ὀδούς, ὀλοθρευτής, ὀλοθρεύω, ὀμίχλη.
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

    # (id, new_strongs, note, is_snap)  is_snap True => resolve the auto:strongs-snap row
    fixes = [
        (3105, "G3385", "μήτι; wrong snap to μήτε G3383", True),
        (3145, "G3429", "μοιχάω; wrong snap to οἴχομαι G8468", True),
        (3146, "G3429", "μοιχάω (2nd μοιχάομαι entry); wrong snap to οἴχομαι G8468", True),
        (3220, "G3501", "νέος comparative; wrong snap to ἀνώτερος G0511", True),
        (3319, "G6064", "οἰκετεία EXACT G6064; wrong snap to οἰκέτις (accent hid exact)", True),
        (3119, "G3403", "μιμνήσκω; middle-form lemma missed exact-match", False),
        (3175, "G3460", "Μύρα; double-form lemma missed exact-match", False),
        (3294, "G3588", "ὁ ἡ τό definite article (page 466)", False),
        (3295, "G3588", "ὁ ἡ τό article continuation (page 467)", False),
        (3308, "G3600", "ὀδυνάω; middle-form lemma missed exact-match", False),
        (3344, "G3633", "οἴομαι; double-form lemma missed exact-match", False),
        (3380, "G3660", "ὀμνύω; double-form lemma missed exact-match", False),
        (3349, "G_N/A", "οἱοσδηποτοῦν; only disputed Jn 5:4 Lachmann reading — no Strong's", False),
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
