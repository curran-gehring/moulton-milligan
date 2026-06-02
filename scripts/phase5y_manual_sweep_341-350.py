"""Phase 5y: one-shot manual sweep of residual disagreements for wave AE.

Pages 341-350 (book 311-320): Κ section καθάπτω→κανών. Phase-2 audit 84.3%
agree+minor (just below gate, NON-systemic continuation/citation noise;
lesson #1 = no prompt-refine). phase5_resolve.py auto-closed 10 (5 accept-note +
3 has-translation + 2 reviewer-superset). This script corrects 1 reviewer-superset
(literary), adopts 1 NT-ref add, keep-producer on 6.

Phase-3 keying: 67 exact + 2 snaps + 1 NULL. KEEP snap Καιάφας->G2533 (diaeresis
of Καϊάφας). BAD snap re-keyed: κακοπαθία->G2552 (was κακοπραγία G20553, wrong-stem
+extended; κακοπαθία=κακοπάθεια, Jas 5:10). NULL->G_N/A: καθολικός (non-NT; adj only
in the titles of the 'Catholic' Epistles, not NT text). HOMOGRAPH FIX (applied):
p344 καί G1499->G2532 (exact-match wrongly picked εἰ καί G1499; entry is simple/
paratactic καί). 2 ἵνα confirmed G2443.

p346 NOTE: vision OCR listed κακοήθεια out of alphabetical order (last instead of
4th, between κακία and κακολογέω). Content intact + cleanly separated from
κακοποιέω; entries are keyed by lemma so intra-page position is metadata only.
Left as-OCR'd (faithful to the scan pass; zero impact on keyed deliverable).

revert-reviewer-superset (1):
  d#724 καλύπτω: 'Aristeas 87' = Letter of Aristeas (literary/pseudepigraphon) ->
    body; revert to producer. (d#710 καθημερινός 'London papyrus Inv. 1885' is
    documentary papyri -> KEEP, auto-resolution stands.)

adopt-reviewer (1):
  d#714 καί nt_refs: add 'Jn 9⁷·¹¹' — body has '...than the corresponding passage
    in St. John [9⁷·¹¹]', a real NT ref the producer missed. Adopt reviewer list.

keep-producer (6):
  d#712 καθό lemma: producer acute 'καθό' (lemma/citation form, keys G2526) vs
    reviewer grave 'καθὸ' (contextual accent). Keep producer.
  d#713 καί papyri: first P Par citation completeness — full text is in body;
    Phase 4 normalizes. Keep producer.
  d#715 Καιάφας lemma: clean 'Καιάφας' (keys G2533) vs reviewer 'Καιάφας (or
    Καιφᾶς)'; the (or Καιφᾶς) variant belongs in body. Keep producer.
  d#716 Καιάφας body: producer keeps '(or Καιφᾶς).' at body head (the alt form).
    Keep producer (pairs with d#715).
  d#717 καινός papyri: bare '406¹⁷' anaphoric to P Tebt; Phase 4 normalizes. Keep.
  d#721 κακοπαθία papyri: '246' inherits Syll (anaphora); Phase 4 normalizes. Keep.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

KEEP_PRODUCER = {
    712: "producer acute 'καθό' is the lemma/citation form (keys G2526); reviewer grave 'καθὸ' is contextual; keep producer",
    713: "first P Par citation completeness — full text in body; Phase 4 normalizes; keep producer",
    715: "clean lemma 'Καιάφας' keys G2533; '(or Καιφᾶς)' variant belongs in body; keep producer",
    716: "producer keeps '(or Καιφᾶς).' alt-form at body head; keep producer (pairs with d#715)",
    717: "bare '406¹⁷' anaphoric to P Tebt; Phase 4 normalizes anaphora; keep producer",
    721: "'246' inherits Syll (citation anaphora); Phase 4 normalizes; keep producer",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    reverted = adopted = kept = skipped = 0

    with con:
        # revert reviewer-superset d#724 (Aristeas literary -> body)
        d = con.execute("SELECT entry_id, producer_value FROM disagreements WHERE id=724").fetchone()
        if d:
            con.execute("UPDATE entries SET papyri_citations=? WHERE id=?", (d["producer_value"], d["entry_id"]))
            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=724",
                ("'Aristeas 87' = Letter of Aristeas (literary/pseudepigraphon) -> body; revert to producer",
                 "manual:keep-producer (literary -> body)", now),
            )
            reverted += 1

        # adopt-reviewer d#714 (καί += Jn 9⁷·¹¹, attested in body 'St. John [9⁷·¹¹]')
        d = con.execute("SELECT entry_id, reviewer_value, resolution FROM disagreements WHERE id=714").fetchone()
        if d and d["resolution"] is None:
            con.execute("UPDATE entries SET nt_references=? WHERE id=?", (d["reviewer_value"], d["entry_id"]))
            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=714 AND resolution IS NULL",
                ("adopt reviewer: body has '...corresponding passage in St. John [9⁷·¹¹]' — real NT ref producer missed",
                 "manual:adopt-reviewer", now),
            )
            adopted += 1

        for did, note in KEEP_PRODUCER.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1
                continue
            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=? AND resolution IS NULL",
                (note, "manual:keep-producer", now, did),
            )
            kept += 1

    print(f"revert reviewer-superset (literary -> body): {reverted}")
    print(f"adopt-reviewer (καί += Jn 9⁷·¹¹): {adopted}")
    print(f"keep-producer: {kept}")
    print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
