"""Phase 3b: keying + lemma corrections for the 361-400 batch.

Applies the adjudicated fixes found during snap-inspection + OCR cross-check:

p361 OCR-headword trio (vision OCR mislabeled 3 headwords; audit flagged as
majors; verified against the page image):
  id 2498 "καταπέτασμα"#1 -> καταπαύω G2664  (body was about καταπαυστικός, a
          musical pause from Philodemus; OCR rendered the lemma as a 2nd
          καταπέτασμα and the cited word as κατασπασμός)
  id 2503 "καταποντόω"    -> καταπονέω G2669  (Ac 7:24, 2 Pet 2:7 "oppress";
          OCR: καταπονούμενος -> καταπτονόμενος; nt-refs 7³⁴/2³ -> 7²⁴/2⁷)
  id 2504 "καταπτύω"      -> καταποντίζω G2670 (Mt 14:30, 18:6 "sink"; only two
          NT occurrences, so OCR 14³⁵/18⁸ -> 14³⁰/18⁶ is unambiguous)

Bad fuzzy-snaps re-keyed (snap-audit dry-run independently REJECTed all of
these; promote auto:strongs-snap -> manual:strongs-fix to protect):
  id 2606 κερέα   G2768->G2762  (κεραία "tittle" Mt 5:18; snapped to κέρας horn)
  id 2694 κόλλημα G2814->G_N/A  (papyrus-sheet join, non-NT; snapped to κλῆμα branch)
  id 2716 κόπριον G8071->G2874  (κοπρία "dung" Lk 13:8; snapped to κόριον)
  id 2799 κωμός   G1041->G2970  (κῶμος "revel"; snapped to βωμός altar)

Kept-but-protected snap (snap-audit REJECT is over-pedantic, same pattern as
Ἰτουραῖος/κατάθεμα — Mt 27:6 κορβανᾶν IS tagged G2878):
  id 2720 κορβανᾶς G2878 (promote snap -> manual:strongs-fix; no re-key)

G_N/A rescues (real NT words that missed exact-match on the index lemma form):
  id 2633 "κίχρημι or χράω"  -> G5531 (χράω "lend" Lk 11:5)
  id 2675 κοιμάομαι           -> G2837 (index lemma κοιμάω)
  id 2707 κομψῶς              -> G2866 (Jn 4:52 κομψότερον; reachability key)
  id 2745 "κρείσσων, κρείττων"-> G2909 (index lemma κρείττων)
  id 2778 κυλισμός            -> G2946 (index lemma κύλισμα; 2 Pet 2:22)
  id 2800 Κῶς                 -> G2972 (Cos, Ac 21:1)

Merge: id 2797 "κωλυτής" (p397) is the tail of the κωλύω entry (p396 id 2796),
not a separate lemma (snapped wrongly to ἀκωλύτως G0209). Append its body to
id 2796 and delete id 2797 (+ its disagreements).
"""
from __future__ import annotations

import json
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

    with con:
        # --- p361 trio: lemma + strongs + nt_references + body OCR ---
        trio = [
            (2498, "καταπαύω", "G2664", None,
             [("κατασπασμός", "καταπαυστικός")]),
            (2503, "καταπονέω", "G2669", ["Ac 7²⁴", "2 Pet 2⁷"],
             [("καταπτονόμενος", "καταπονούμενος")]),
            (2504, "καταποντίζω", "G2670", ["Mt 14³⁰", "Mt 18⁶"],
             [("14³⁵, 18⁸", "14³⁰, 18⁶")]),
        ]
        for eid, lemma, strongs, nt, body_subs in trio:
            r = con.execute("SELECT body_markdown FROM entries WHERE id=?", (eid,)).fetchone()
            body = r["body_markdown"] or ""
            for old, new in body_subs:
                body = body.replace(old, new)
            if nt is not None:
                con.execute("UPDATE entries SET lemma_greek=?, strongs=?, nt_references=?, body_markdown=? WHERE id=?",
                            (lemma, strongs, json.dumps(nt, ensure_ascii=False), body, eid))
            else:
                con.execute("UPDATE entries SET lemma_greek=?, strongs=?, body_markdown=? WHERE id=?",
                            (lemma, strongs, body, eid))
            # resolve any open lemma-disagreement (audit major) for this entry
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE entry_id=? AND resolution IS NULL""",
                        (f"OCR-headword fix: relabel to {lemma} ({strongs}); verified vs page image",
                         "manual:lemma-fix", now, eid))
            n += 1

        # --- bad-snap re-keys (promote snap disagreement -> manual:strongs-fix) ---
        snap_fixes = [
            (2606, "G2762", "κερέα=κεραία 'tittle' Mt 5:18; was wrong-stem snap to κέρας"),
            (2694, "G_N/A", "κόλλημα papyrus-sheet join, non-NT; was wrong-stem snap to κλῆμα"),
            (2716, "G2874", "κόπριον=κοπρία 'dung' Lk 13:8; was wrong snap to κόριον"),
            (2799, "G2970", "κωμός=κῶμος 'revel'; was wrong snap to βωμός"),
        ]
        for eid, strongs, note in snap_fixes:
            con.execute("UPDATE entries SET strongs=? WHERE id=?", (strongs, eid))
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE entry_id=? AND resolution_by='auto:strongs-snap' AND resolution IS NULL""",
                        (note, "manual:strongs-fix", now, eid))
            n += 1

        # --- kept-but-protected snap (κορβανᾶς) ---
        con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                       WHERE entry_id=2720 AND resolution_by='auto:strongs-snap' AND resolution IS NULL""",
                    ("κορβανᾶς->G2878 is a valid reachability key (Mt 27:6 κορβανᾶν tagged G2878); "
                     "snap-audit REJECT over-pedantic, protect", "manual:strongs-fix", now))
        n += 1

        # --- G_N/A rescues ---
        rescues = [
            (2633, "G5531", "χράω 'lend' Lk 11:5; index lemma differs from 'κίχρημι or χράω'"),
            (2675, "G2837", "κοιμάομαι; index lemma κοιμάω"),
            (2707, "G2866", "κομψῶς illustrates Jn 4:52 κομψότερον; reachability key G2866"),
            (2745, "G2909", "κρείσσων/κρείττων; index lemma κρείττων"),
            (2778, "G2946", "κυλισμός; index lemma κύλισμα; 2 Pet 2:22"),
            (2800, "G2972", "Κῶς 'Cos' Ac 21:1; index lemma Κώς"),
        ]
        for eid, strongs, note in rescues:
            con.execute("UPDATE entries SET strongs=? WHERE id=?", (strongs, eid))
            n += 1

        # --- merge κωλυτής (2797) tail into κωλύω (2796), delete fragment ---
        frag = con.execute("SELECT body_markdown FROM entries WHERE id=2797").fetchone()
        head = con.execute("SELECT body_markdown FROM entries WHERE id=2796").fetchone()
        if frag and head:
            merged = (head["body_markdown"].rstrip() + " " + frag["body_markdown"].lstrip()).strip()
            con.execute("UPDATE entries SET body_markdown=? WHERE id=2796", (merged,))
            con.execute("DELETE FROM disagreements WHERE entry_id=2797")
            con.execute("DELETE FROM reviews WHERE entry_id=2797")
            con.execute("DELETE FROM entries WHERE id=2797")
            n += 1

    print(f"applied {n} fix groups")
    # quick verification
    for eid in (2498, 2503, 2504, 2606, 2694, 2716, 2799, 2633, 2675, 2707, 2745, 2778, 2800):
        r = con.execute("SELECT id,lemma_greek,strongs FROM entries WHERE id=?", (eid,)).fetchone()
        if r:
            print(f"  id={r['id']} {r['lemma_greek']} -> {r['strongs']}")
    print("  id=2797 deleted:", con.execute("SELECT COUNT(*) FROM entries WHERE id=2797").fetchone()[0] == 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
