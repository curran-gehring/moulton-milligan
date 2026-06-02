"""Phase 5p: one-shot manual sweep of residual disagreements for wave V.

Pages 251-260 (ἐξ-/ἐπ- compounds). Mirrors phase5b-o. Phase-2 audit 93.4% agree+minor
(comfortably above gate — the ἐξ-/ἐπ- stretch is less continuation-heavy than wave-U's
ἐν-). phase5_resolve.py auto-closed 10 (8 continuation + 2 legit superset citation adds:
ἑξῆς P Hamb, ἐπανίστημι Catalogus codd. astr. gr.). This script handles the residual 3.

Phase-3 keying: 81 exact + 5 snaps + 5 unmatched. Snap-audit: 3 KEEP (ἐξεραυνάω→G1830
αυ/ευ, ἐπαρχεία→G1885 ει/ι) + 2 REJECT→G_N/A (ἐξηλόω×2 'unfasten/unnail' ↛ δηλόω
'make clear' — different lexemes, and ἐξηλόω is non-NT papyri). One more BAD snap caught
pre-audit: ἔοικα→G3614 (οἰκία 'house') is wrong; ἔοικα (Jas 1:6,23) = G1503 (index stores
it under lemma εἴκω, so exact match missed it; G1503 ≠ G1502, both spelled εἴκω). Manually
re-keyed in Phase 3.

5 unmatched resolved in Phase 3: ἐξίστημι/ἐξιστάω/ἐξιστάνω→G1839, ἐξουδενέω/ἐξουθενέω→G1848
(dominant NT form; ἐξουδενέω=G1847 Mk 9:12 noted), ἐπαγγέλλομαι×2→G1861 (middle of
ἐπαγγέλλω; index stores active) — BUT one was a mislabel, see below; ἐπαναγκάζω→G_N/A
(non-NT), ἔξειμι id 1718→G_N/A (the 'from εἰμί, see s.v. ἔξεστι' cross-ref stub homograph;
ἔξεστι G1832 covered by the ἐξόν entry; the real ἔξειμι go-out homograph id 1717 = G1826).

relabels (2 — both parser-invented headwords for continuation tails, Codex flagged):
  id 1721 (p253 pos 1): parser labeled 'ἐξαιρέω' (dup of the real p251 ἐξαιρέω) but the body
    ('ἐξελκύσαντα τὸ βέλος' — drew out the arrow) is the CONTINUATION of p252's ἐξέλκω entry
    (id 1720, G1828). Codex reviewer said ἐξελκύω (alt present of the same verb). Relabel
    →ἐξέλκω (match p252 headword for Phase-6 dedup), re-key G1807→G1828.
  id 1755 (p257 pos 1): parser labeled 'ἐπαγγέλλομαι' but it's the CONTINUATION of p256's
    ἐπαγγελία (NOUN) entry ('the promises are almost = threats'). Codex reviewer said
    ἐπαγγελία. Relabel →ἐπαγγελία, re-key G1861(verb)→G1860(noun). (The real verb entry is
    id 1756 pos 2, correctly G1861.)

keep_producer (1):
  d#497 ἑορτή nt_refs: 'Ac 18²¹' vs reviewer 'Ac 18²¹ D' — the 'D' is a Codex-Bezae witness
    siglum (editorial); the bare verse ref links correctly in FirstWord. Keep producer.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

KEEP: dict[int, str] = {
    497: "reviewer adds 'D' (Codex Bezae witness siglum) to Ac 18²¹; editorial — bare verse ref links correctly, keep producer",
}

# disagreement id -> (entry_id, new_lemma, new_strongs, new_translit)
RELABEL = {
    492: (1721, "ἐξέλκω", "G1828", "exélkō"),
    498: (1755, "ἐπαγγελία", "G1860", "epangelía"),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = relabeled = skipped = 0

    with con:
        # ---- relabels (lemma + strongs) ----
        for did, (eid, lemma, strongs, translit) in RELABEL.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            cur = con.execute("SELECT lemma_greek, strongs FROM entries WHERE id=?", (eid,)).fetchone()
            con.execute("UPDATE entries SET lemma_greek=?, strongs=?, lemma_translit=? WHERE id=?",
                        (lemma, strongs, translit, eid))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL",
                        (f"relabel continuation tail: {cur['lemma_greek']}({cur['strongs']}) -> {lemma}({strongs}); "
                         f"parser-invented headword for a prior-page continuation; Phase-6 longest-body-wins folds it in",
                         "manual:lemma-fix", now, did))
            relabeled += 1

        # ---- keep-producer ----
        for did, note in KEEP.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

    print(f"\nrelabeled: {relabeled}")
    print(f"applied (keep-producer): {applied}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
