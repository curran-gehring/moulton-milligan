"""Phase 3b: keying corrections for the 401-440 batch.

Bad fuzzy-snaps re-keyed (wrong-stem; snap-audit dry-run independently REJECTs;
promote auto:strongs-snap -> manual:strongs-fix):
  id 3003 μέλει        G3192->G3199  (μέλω 'it is a care'; snapped to μέλι honey)
  id 3043 μεταβάλλομαι G3338->G3328  (μεταβάλλω Ac 28:6; snapped to μεταμέλομαι)
  id 3100 μήπου        G1222->G_N/A  (cross-ref stub "See s.v. μήπω"; snapped to δήπου)

G_N/A rescues (real NT words that missed exact-match on the index lemma form):
  id 2879 λογ(ε)ία              -> G3048 (λογία 'collection' 1 Cor 16:1,2)
  id 2919 "μαγία, μαγεία"       -> G3095 (μαγεία 'magic' Ac 8:11)
  id 2994 "μεθιστάνω, μεθίστημι"-> G3179 (μεθίστημι; the REAL entry — id 2993 is
           a μέθη-continuation mislabeled μεθιστάνω, handled by merge in phase5)
  id 3061 μεταπέμπομαι          -> G3343 (μεταπέμπω, Ac 10:5 etc.)
  id 3069 μετεωρίζομαι          -> G3349 (μετεωρίζω, Lk 12:29)
  id 3082 "μέχρι, μέχρις"       -> G3360 (μέχρι 'until')

Continuation-fragment snaps cleared (these are tails mislabeled with the running-
header LEFT lemma; phase5 merges them into their prior-page head, then deletes):
  id 2993 "μεθιστάνω" (body = μέθη tail)   -> G_N/A  (merge into p423 μέθη)
  id 3079 "μέτριος"   (body = μετρίως tail)-> G_N/A  (merge into p436 μετρίως)

KEEP snaps (legit spelling/case/variant — left as auto:strongs-snap, confirmed by
snap-audit dry-run): Λασέα, λάσκω, λεγιών, λῆ(μ)ψις, λυσιτελέω, Μαθθαῖος, μαμωνᾶς,
μαραναθά, Μᾶρκος x2, μασθός, μεθοδία, μεθόριον, μενοῦν, μεταμέλομαι, μήγε.
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

    # (id, new_strongs, note, is_snap)  — is_snap True => resolve auto:strongs-snap row
    fixes = [
        (3003, "G3199", "μέλω 'it is a care'; wrong snap to μέλι honey", True),
        (3043, "G3328", "μεταβάλλω Ac 28:6; wrong snap to μεταμέλομαι", True),
        (3100, "G_N/A", "cross-ref stub 'See s.v. μήπω'; wrong snap to δήπου", True),
        (2879, "G3048", "λογία 'collection' 1 Cor 16:1,2; missed exact-match on '(ε)' form", False),
        (2919, "G3095", "μαγεία 'magic' Ac 8:11; double-form lemma missed exact-match", False),
        (2994, "G3179", "μεθίστημι; double-form lemma missed exact-match", False),
        (3061, "G3343", "μεταπέμπω Ac 10:5 etc.", False),
        (3069, "G3349", "μετεωρίζω Lk 12:29", False),
        (3082, "G3360", "μέχρι 'until'; double-form lemma missed exact-match", False),
        (2993, "G_N/A", "μέθη continuation mislabeled μεθιστάνω; clear wrong snap (merged in phase5)", True),
        (3079, "G_N/A", "μετρίως continuation mislabeled μέτριος; clear wrong snap (merged in phase5)", True),
    ]
    with con:
        for eid, strongs, note, is_snap in fixes:
            con.execute("UPDATE entries SET strongs=? WHERE id=?", (strongs, eid))
            if is_snap:
                con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                               WHERE entry_id=? AND resolution_by='auto:strongs-snap' AND resolution IS NULL""",
                            (note, "manual:strongs-fix", now, eid))
            n += 1

    print(f"applied {n} fixes")
    for eid, strongs, *_ in fixes:
        r = con.execute("SELECT id,lemma_greek,strongs FROM entries WHERE id=?", (eid,)).fetchone()
        print(f"  id={r['id']} {r['lemma_greek']} -> {r['strongs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
