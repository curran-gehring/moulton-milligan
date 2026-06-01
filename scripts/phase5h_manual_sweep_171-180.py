"""Phase 5h: one-shot manual sweep of residual disagreements for wave N.

Pages 171-180 (Δ section; parsed 2026-06-01). Mirrors phase5b-g.
phase5_resolve.py already auto-closed 7 continuation-notes. This encodes the
8 manual residuals + 2 keying fixes from the Phase-3 snap-audit / lemma review.

Two OCR-split / mislabeled-continuation lemma fixes (the substantive ones):

  δέσμη MERGE (d#287). The vision OCR placed the TAIL of the δέσμη entry at the
    very top of p172 (alphabetically impossible as a real prior-page continuation:
    δέσμη sorts after δερμάτινος/δέρρις/δέρω/δεσμεύω, all of which follow it on the
    page). The parser mislabeled that tail "δέρμα" (entry 1115) and also emitted
    the δέσμη headword+start as entry 1120 (body opens mid-sentence "is differently
    accented..."). They are ONE entry. Merge: append 1115's body/citations/nt into
    1120 (reading order head→tail), keep 1120 as δέσμη=G1197, DELETE 1115 (+its
    review/disagreement rows). Prevents Phase-6 longest-body dedup from silently
    dropping half the entry (incl. the Mt 13³⁰ ref + δεσμίδιον/δύσμη material).

  δέχομαι RELABEL (d#289). p174 opens with the tail of p173's truncated δέχομαι
    entry ("from P Leid M ii.7 ... ὃν ἐδέξατο ... 'receive,' 'accept.'"), THEN the
    "## δέω." headword. The parser labeled the continuation δέω (same as the real
    headword that follows -> two δέω rows). Relabel entry 1133 δέω->δέχομαι, key
    G1209. Entry 1134 (the true ## δέω headword) correctly stays δέω=G1210.

Keying fix (article-tag-in-lemma, same class as wave-M δεῖνα):
  δέον (entry 1112): parser folded the article into the lemma ("δέον, τό");
    unmatched. Clean to "δέον" and key G1163 (δεῖ) — NT tags the neuter participle
    δέον (Ac 19³⁶, 1 Pet 1⁶, 1 Tim 5¹³) to δεῖ.

  (δηλαυγῶς entry stays NULL->G_N/A: snap to τηλαυγῶς G5081 was Codex-REJECTed —
   δηλ- 'clear' vs τηλ- 'far' are distinct lexemes; δηλαυγῶς is only a Mk 8:25
   variant reading with no Strong's of its own. Its G_N/A tombstone is correct.)

Plain disagreements (6):
  add_papyri d#293 δημόσιος: body has "A Leipzig papyrus of Hadrian's reign
    (Inv 2667) has τὴν βασιλικὴν..." — a named citation the producer dropped.
  keep_producer:
    d#288 δεσμεύω: "1ˢ³,¹¹,¹²" line-refs; raw-as-written, Phase 4
    d#291 δέω body: producer "defixio" clean vs reviewer "def-xio" garbled
    d#297 διαθήκη nt: reviewer wanted "4 Kings 23²¹" (OT/LXX — barred by NT-only
      rule, belongs in body) + "Lk 22⁸" (NOT in the body at all). Producer correct.
    d#299 διακούω papyri / d#300 διαλείπω papyri: reviewer appended prose
      annotations ("—petition to the Praefect" etc.); keep raw citation.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

DECISIONS: dict[int, tuple] = {
    288: ("keep_producer", "'1ˢ³,¹¹,¹²' line cross-refs within P Oxy VII. 1049; raw-as-written, Phase 4"),
    291: ("keep_producer", "producer 'defixio' clean; reviewer 'def-xio' is OCR garble"),
    297: ("keep_producer", "reviewer adds OT '4 Kings 23²¹' (barred by NT-only rule) + unattested 'Lk 22⁸'; producer correct"),
    299: ("keep_producer", "reviewer appended prose annotations to citations; keep raw-as-written"),
    300: ("keep_producer", "reviewer appended prose annotation ('complaint against a husband'); keep raw"),
    293: ("add_papyri", "Leipzig papyrus of Hadrian's reign (Inv 2667)", None,
          "body: 'A Leipzig papyrus of Hadrian's reign (Inv 2667) has τὴν βασιλικὴν...' — dropped named citation"),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = papyri_added = 0
    skipped = 0

    with con:
        # ---- plain disagreement decisions ----
        for did, dec in DECISIONS.items():
            row = con.execute("SELECT entry_id, resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            kind = dec[0]; eid = row["entry_id"]
            if kind == "keep_producer":
                resolution, by = dec[1], "manual:keep-producer"
            elif kind == "add_papyri":
                cite, _, note = dec[1], dec[2], dec[3]
                er = con.execute("SELECT papyri_citations FROM entries WHERE id=?", (eid,)).fetchone()
                arr = json.loads(er["papyri_citations"] or "[]")
                if cite not in arr:
                    arr.append(cite)
                    con.execute("UPDATE entries SET papyri_citations=? WHERE id=?",
                                (json.dumps(arr, ensure_ascii=False), eid))
                    papyri_added += 1
                resolution, by = note, "manual:accept-reviewer"
            else:
                print(f"  d#{did}: unknown kind"); continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (resolution, by, now, did))
            applied += 1

        # ---- δέσμη MERGE (1115 tail -> 1120 head); delete 1115 ----
        head = con.execute("SELECT id,body_markdown,papyri_citations,nt_references,strongs FROM entries WHERE id=1120").fetchone()
        tail = con.execute("SELECT id,body_markdown,papyri_citations,nt_references FROM entries WHERE id=1115").fetchone()
        merged = 0
        if head and tail:
            new_body = (head["body_markdown"] or "").rstrip() + " " + (tail["body_markdown"] or "").lstrip()
            pap = json.loads(head["papyri_citations"] or "[]") + [c for c in json.loads(tail["papyri_citations"] or "[]")
                                                                   if c not in json.loads(head["papyri_citations"] or "[]")]
            nt = json.loads(head["nt_references"] or "[]") + [r for r in json.loads(tail["nt_references"] or "[]")
                                                              if r not in json.loads(head["nt_references"] or "[]")]
            con.execute("UPDATE entries SET body_markdown=?, papyri_citations=?, nt_references=?, strongs='G1197', lemma_translit='désmē' WHERE id=1120",
                        (new_body, json.dumps(pap, ensure_ascii=False), json.dumps(nt, ensure_ascii=False)))
            # record the merge on the surviving row
            con.execute("""INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value,
                           resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)""",
                        (1120, "body_markdown", "δέσμη headword body only (entry 1120)",
                         "OCR-split tail (entry 1115, mislabeled δέρμα) merged in",
                         "merged OCR-split δέσμη fragment 1115->1120; 1115 deleted", "manual:merge", now))
            # resolve + delete the mislabeled-δέρμα row 1115 and its review/disagreement rows
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE entry_id=1115 AND resolution IS NULL",
                        ("entry 1115 (mislabeled δέρμα) was the OCR-split tail of δέσμη; merged into 1120 and deleted",
                         "manual:merge", now))
            con.execute("DELETE FROM reviews WHERE entry_id=1115")
            con.execute("DELETE FROM disagreements WHERE entry_id=1115")
            con.execute("DELETE FROM entries WHERE id=1115")
            merged = 1

        # ---- δέχομαι RELABEL (1133: δέω -> δέχομαι, key G1209) ----
        e = con.execute("SELECT lemma_greek,strongs FROM entries WHERE id=1133").fetchone()
        relabeled = 0
        if e and e["lemma_greek"] != "δέχομαι":
            con.execute("UPDATE entries SET lemma_greek='δέχομαι', strongs='G1209', lemma_translit='déchomai' WHERE id=1133")
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=289 AND resolution IS NULL",
                        ("continuation of p173's truncated δέχομαι; parser mislabeled it δέω (the following headword). Relabeled + keyed G1209.",
                         "manual:lemma-swap", now))
            relabeled = 1

        # ---- δέον cleanup (1112: 'δέον, τό' -> 'δέον', key G1163) ----
        e = con.execute("SELECT lemma_greek,strongs FROM entries WHERE id=1112").fetchone()
        deon_fixed = 0
        if e and e["strongs"] != "G1163":
            con.execute("UPDATE entries SET lemma_greek='δέον', strongs='G1163', lemma_translit='deî' WHERE id=1112")
            con.execute("""INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value,
                           resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)""",
                        (1112, "strongs", "NULL (unmatched; lemma had article tag 'δέον, τό')", "G1163",
                         "cleaned lemma 'δέον, τό'->'δέον'; NT tags the participle δέον (Ac 19³⁶, 1 Pet 1⁶) to δεῖ G1163",
                         "manual:strongs-fix", now))
            deon_fixed = 1

    print(f"\napplied (disagreements): {applied}")
    print(f"papyri added:            {papyri_added}")
    print(f"δέσμη merge (1115->1120): {merged}")
    print(f"δέχομαι relabel (1133):  {relabeled}")
    print(f"δέον key fix (1112):     {deon_fixed}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
