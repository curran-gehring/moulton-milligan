"""Phase 5z: one-shot manual sweep of residual disagreements for wave AF.

Pages 351-360 (book 321-330): κανών→καταξιόω, incl. the κατά preposition
MEGA-ENTRY spanning 352→353→354. Phase-2 audit 86.3% agree+minor (ABOVE the 85%
gate — best wave this session). phase5_resolve.py auto-closed 13 (8 accept-note +
3 has-translation + 2 reviewer-superset). This script corrects 1 reviewer-superset
(literary), adopts 4 NT-ref/date/body fixes, keep-producer on 2.

Phase-3 keying: 76 exact + 3 snaps + 1 NULL. KEEP snaps κατάθεμα->G2652 (Rev 22:3;
index lists fuller TR-variant κατανάθεμα, same Strong's — snap-audit dry-run
REJECTed on stem pedantry but G2652 IS κατάθεμα, so protected manual:strongs-fix),
καταθεματίζω->G2653 (Mt 26:74, same κατανα- variant situation). BAD snap re-keyed:
καταλέγομαι->G2639 (was καταδέομαι G7833 wrong-stem+extended; middle of καταλέγω,
1 Tim 5:9 — snap-audit KEEP). NULL->manual key: κατακαλύπτομαι->G2619 (index has
active κατακαλύπτω; MM headword is middle, 1 Cor 11:6,7). HOMOGRAPH (Tier-1 applied):
καταδέω G20566->G2611 (classic-over-extended, Lk 10:34); καρπός G2590 confirmed.

p354/p355 NOTE: two-column OCR scrambled intra-page entry order (alphabetically-
later καταβ-/καταγγ- before earlier καταγ-). All entries present + keyed by lemma,
so position is metadata only. Left as-OCR'd. καταξιόω (p360 last) spills to p361
(Tesseract-only next batch) so it stays partial until that batch is processed.

revert-reviewer-superset (1):
  d#744 καταλαμβάνω: 'Vett. Val. p. 225⁶' (classical author) mixed with the add ->
    revert to producer (the Herculaneum 176 papyrus + Vett. Val. both remain in
    body_markdown; nothing lost). (d#737 καταδέω '399 (= I. p. 94)' is documentary
    P Lond -> KEEP, auto-resolution stands.)

adopt-reviewer (4):
  d#739 κατακλίνω papyri: restore dropped date '(early i/A.D.)' on P Oxy VIII.
    1088²⁹ (citation as-written includes its date).
  d#745 καταλαμβάνω nt_refs: producer dropped the book prefix on a chained ref
    ('1⁵' should be 'Jn 1⁵'); set clean corrected list (brackets dropped for
    verse-linking; pericope-adulterae status stays in body).
  d#747 καταλλάσσω body: remove the 'PART IV' running section-marker that bled
    into the entry body (adopt reviewer's cleaned body).
  d#748 καταλύω nt_refs: producer dropped book prefix ('19⁷' should be 'Lk 19⁷');
    adopt reviewer's prefixed list.

keep-producer (2):
  d#743 κατακύπτω nt_refs: keep clean 'Jn 8⁸' (no '[Jn]' bracket — clean for
    verse-linking; the pericope-adulterae marker stays in body).
  d#750 καταντάω papyri: bare '105⁸' anaphoric to ib.; Phase 4 normalizes. Keep.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

# d#745 corrected nt_references: fix 'Jn' prefix on 1:5, drop text-critical brackets
D745_NT = ["Jn 12³⁵", "Jn 1⁵", "1 Th 5⁴", "Jn 8³ f.", "Ac 4¹³"]

KEEP_PRODUCER = {
    743: "keep clean 'Jn 8⁸' (no '[Jn]' bracket — clean for verse-linking; pericope-adulterae marker stays in body)",
    750: "bare '105⁸' anaphoric to ib.; Phase 4 normalizes; keep producer",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    reverted = adopted = kept = skipped = 0

    with con:
        # revert reviewer-superset d#744 (Vett. Val. literary mixed in)
        d = con.execute("SELECT entry_id, producer_value FROM disagreements WHERE id=744").fetchone()
        if d:
            con.execute("UPDATE entries SET papyri_citations=? WHERE id=?", (d["producer_value"], d["entry_id"]))
            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=744",
                ("Vett. Val. (classical author) mixed into the add; revert to producer (refs remain in body)",
                 "manual:keep-producer (literary -> body)", now),
            )
            reverted += 1

        # adopt-reviewer: d#739 (date), d#747 (body PART IV removal), d#748 (Lk prefix) -> reviewer_value
        for did, note in {
            739: "adopt reviewer: restore dropped date '(early i/A.D.)' on the P Oxy citation (as-written)",
            747: "adopt reviewer: remove 'PART IV' running section-marker that bled into the body",
            748: "adopt reviewer: restore book prefix '19⁷'->'Lk 19⁷' on the chained ref",
        }.items():
            d = con.execute("SELECT entry_id, field, reviewer_value, resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not d or d["resolution"] is not None:
                skipped += 1
                continue
            col = {"papyri_citations_raw": "papyri_citations", "nt_references_raw": "nt_references",
                   "body_markdown": "body_markdown", "lemma_greek": "lemma_greek"}[d["field"]]
            con.execute(f"UPDATE entries SET {col}=? WHERE id=?", (d["reviewer_value"], d["entry_id"]))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=? AND resolution IS NULL",
                        (note, "manual:adopt-reviewer", now, did))
            adopted += 1

        # adopt-reviewer custom: d#745 nt_refs corrected list
        d = con.execute("SELECT entry_id, resolution FROM disagreements WHERE id=745").fetchone()
        if d and d["resolution"] is None:
            con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                        (json.dumps(D745_NT, ensure_ascii=False), d["entry_id"]))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=745 AND resolution IS NULL",
                        ("adopt reviewer (corrected): fix dropped book prefix '1⁵'->'Jn 1⁵'; drop text-critical brackets for clean verse-linking",
                         "manual:adopt-reviewer", now))
            adopted += 1

        for did, note in KEEP_PRODUCER.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1
                continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=? AND resolution IS NULL",
                        (note, "manual:keep-producer", now, did))
            kept += 1

    print(f"revert reviewer-superset (literary -> body): {reverted}")
    print(f"adopt-reviewer (date/body/nt-prefix fixes): {adopted}")
    print(f"keep-producer: {kept}")
    print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
