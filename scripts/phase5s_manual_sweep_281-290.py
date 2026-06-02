"""Phase 5s: one-shot manual sweep of residual disagreements for wave Y.

Pages 281-290 (end of ἐπ-, through ἐρ-/ἑρ-/ἐσθ-/ἕτερος/ἔτι/εὐ-). Mirrors phase5b-r.
Phase-2 audit 84.3% agree+minor — marginally below gate, NON-systemic (continuation-heavy
+ two parser continuation-mislabels on p284/p287 inflating the major count; lesson #1 no
prompt-refine). phase5_resolve.py auto-closed 14 (8 continuation + 4 has-translation + 2
legit epigraphic superset adds: ἐπόπτης JHS, εὐάρεστος Mittheilungen). This script handles
the residual 14.

Phase-3 keying: 81 exact + 1 snap + 1 unmatched; the snap was a MISLABEL (see relabels).
No snap-audit run (the only snap was relabeled away → no new snap to review; avoids
re-litigating prior keeps per the wave-W non-determinism discipline). No homographs.
Unmatched: ἐραυνάω/ἐρευνάω→G2045 (Jn 5:39; αυ/ευ 2-form headword).

relabels done in Phase 3 (resolve the audit's lemma disagreements here):
  d#571 id 1948 (p284): parser invented 'ἕρμα' (snapped to ἅρμα G0716) but it's the
    CONTINUATION of p283's ἔρημος (body continues the Klepht-ballad transl. 'wretched
    arms...' + discusses ἔρμος = MGr ἔρημος). Relabeled →ἔρημος G2048.
  d#584 id 1980 (p287): parser took 'ἑτερόγλωσσος' from the NEXT headword, but it's the
    CONTINUATION of p286's ἑταῖρος (body: 'Aphaeresis in MGr ταίρ' = ταίρι/ἑταῖρος).
    Relabeled →ἑταῖρος G2083; the real ἑτερόγλωσσος (1 Cor 14:21) is id 1981 (G2084).

adopt_reviewer (2 — legit epigraphic/papyri citation reconstructions, no classical authors):
  d#568 ἔπος (id 1932): reviewer reconstructs detached 'Syll 55⁵' + regroups; clean array.
  d#589 εὐαγγέλιον (id 1993): reviewer adds legit front refs (a γνώστης-cross-ref papyrus,
    OGIS 458); clean array, spot-checked free of classical authors.

keep_producer (10):
  d#566 ἐπόπτης nt_refs: reviewer adds 'Esth 5¹' + '2 Macc 7³⁵' = OT + APOCRYPHA, barred
    from nt_references; producer correctly has only 2 Pet 1¹⁶. Keep producer.
  d#574 ἐριθεία lemma / d#575 ἐριθεία body: '(—ία)' variant marker — clean lemma keys
    G2052, marker stays in body (wave-S convention). Keep producer.
  d#577 ἑρμηνευτής nt_refs: reviewer '1 Cor 14²⁸ B' adds Vaticanus witness siglum; bare
    ref links, keep producer.
  d#578 ἑρμηνεύω citations: reviewer adds 'ii. 21' line ref to BGU I. 326; Phase 4.
  d#583 ἔσχατος nt_refs: reviewer 'Mt 12⁴⁵ al.' adds editorial 'al.'; keep producer.
  d#586 ἑτερόγλωσσος body / d#587 ἑτερόγλωσσος nt_refs: producer corrected the OCR slip
    '1 Cor 14³¹' → '1 Cor 14²¹' (the genuine ἑτερόγλωσσος locus); reviewer wants the wrong
    14³¹ back. Keep producer (producer is right).
  d#569 ἐργάζομαι citations: reviewer merely regroups 'ib. 211², 212²' into one element;
    trivial grouping, Phase 4.
  d#588 ἕτερος citations: reviewer restores 'ib.' anaphora ('67' → 'ib. 67'); per-element
    diff (not a clean array adopt), anaphora is Phase-4 territory. Keep producer.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

RELABEL_RESOLVE = {  # disagreement id -> note (lemma already changed in Phase 3)
    571: "lemma relabeled ἕρμα→ἔρημος (G0716→G2048) in Phase 3: continuation of p283 ἔρημος, not a ἕρμα headword",
    584: "lemma relabeled ἑτερόγλωσσος→ἑταῖρος (G2084→G2083) in Phase 3: continuation of p286 ἑταῖρος; real ἑτερόγλωσσος is id 1981",
}

ADOPT = {568: 1932, 589: 1993}  # disagreement id -> entry id (citation reconstruction)

KEEP: dict[int, str] = {
    566: "reviewer adds 'Esth 5¹' (OT) + '2 Macc 7³⁵' (Apocrypha), barred from nt_references; producer correctly has only 2 Pet 1¹⁶",
    574: "variant marker '(—ία)' belongs in body; clean lemma ἐριθεία keys G2052",
    575: "producer keeps '(—ία).' variant marker at body head — legit MM content; keep producer",
    577: "reviewer '1 Cor 14²⁸ B' adds Vaticanus witness siglum; bare ref links, keep producer",
    578: "reviewer adds 'ii. 21' line ref to BGU I. 326; Phase 4 normalizes",
    583: "reviewer 'Mt 12⁴⁵ al.' adds editorial 'al.'; keep producer",
    586: "producer corrected OCR '1 Cor 14³¹'→'14²¹' (genuine ἑτερόγλωσσος locus); reviewer wants wrong 14³¹ back, keep producer",
    587: "producer corrected OCR '1 Cor 14³¹'→'14²¹' (genuine locus); keep producer",
    569: "reviewer merely regroups 'ib. 211², 212²' into one element; trivial grouping, Phase 4",
    588: "reviewer restores 'ib.' anaphora ('67'→'ib. 67'); per-element anaphora diff, Phase 4 territory, keep producer",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    resolved = adopted = applied = skipped = 0

    with con:
        for did, note in RELABEL_RESOLVE.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:lemma-fix", now, did))
            resolved += 1

        for did, eid in ADOPT.items():
            r = con.execute("SELECT resolution, reviewer_value FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE entries SET papyri_citations=? WHERE id=?",
                        (json.dumps(json.loads(r["reviewer_value"]), ensure_ascii=False), eid))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL",
                        ("adopted reviewer's legit epigraphic/papyri citation reconstruction (no classical authors)",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        for did, note in KEEP.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

    print(f"\nrelabel-resolve: {resolved}")
    print(f"adopt-reviewer: {adopted}")
    print(f"keep-producer: {applied}")
    print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
