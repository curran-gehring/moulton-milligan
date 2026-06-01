"""Phase 5k: one-shot manual sweep of residual disagreements for wave Q.

Pages 201-210 (end of Δ -> start of Ε; page 206 is a blank leaf, recorded in
meta.page_206_blank and not parsed). Mirrors phase5b-j. Audit 83.3% agree+minor
— BELOW the 85% gate, but NON-systemic (lesson #1: do NOT prompt-refine). The dip
is the usual continuation/anaphora density amplified by the short 2-entry p205 and
by one fold-forward fragment on p210 (4 disagreement rows on a single entry). All
content is sound; phase5_resolve already auto-applied the safe citation supersets
(incl. δύναμις += "great Paris magical papyrus, 1275 ff.") via
auto:reviewer-superset-citations.

Substantive fix:
  ἐγκομβόομαι fold-forward (d#361/362). p209's ἔγκλημα entry runs over ("...ἴσθι
    μὲν"); p210 opens with its tail "ἔγκλητος ὑπάρχων, '...liable to accusation'
    (Edd.)." which the parser glued onto the FRONT of the ἐγκομβόομαι headword.
    Move the fragment back to ἔγκλημα (entry 1376) and clean ἐγκομβόομαι (1377) to
    start "We have found no instance of this rare verb (1 Pet 5⁵)...". ἐγκομβόομαι
    keeps G1463 + nt [1 Pet 5⁵] (so d#363 'remove 1 Pet 5⁵' is rejected — it IS the
    1 Pet 5:5 verb). Third instance of the wave-O διασπείρω fold-forward pattern.

Keying fixes:
  δυσεντέριον (1341) -> G1420: body ("...settles the form in Ac 28⁸, where all the
    uncials have the neuter") confirms δυσεντέριον is the NT-attested neuter of
    δυσεντερία G1420. Key the parent.
  'ἐγκοπή, ἐγκόπτω' (1378) -> lemma 'ἐγκοπή', G1464: a cross-ref stub ("See
    ἐκκοπή, ἐκκόπτω."); cleaned the doubled lemma to the primary noun and keyed it.
  ἔγγιστα (1367) -> G_N/A tombstone: superlative adverb of ἐγγύς, not an NT lemma
    (NT has ἐγγύς G1451 / ἐγγύτερον G1452). Leave NULL, tombstone so phase3 stops
    re-attempting.

  (δωροφορία 205 + "ἐγκ." 209 already G_N/A via snap-audit reject: δωροφορία is a
   Rom 15:31 variant with no own Strong's; "ἐγκ." is an abbreviation stub.)

keep_producer:
  d#350 δύναμαι / d#355 δῶμα / d#356 δωρεά papyri: reviewer EXPANDS bare-number
    anaphora ("34¹⁰"->"P Hib I. 34¹⁰" etc.); raw-as-written, Phase 4 normalizes
  d#351 δύναμις body: producer em-dash "—" vs reviewer double-hyphen "--"; keep clean
  d#358 ἐάνπερ nt: reviewer wants "Heb 3⁶", but the body says ἐάνπερ is "confined to
    Heb 3¹⁴ (contrast v. 6), 6³" — Heb 3:6 is the CONTRAST (ἐάνπερ does NOT occur
    there); producer correct to omit it
  d#363 ἐγκομβόομαι nt: keep producer [1 Pet 5⁵] (see fold-forward note above)
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

DECISIONS: dict[int, str] = {
    350: "reviewer expands bare 'P Hib I. ...; 34¹⁰' anaphora; raw-as-written, Phase 4",
    351: "producer em-dash '—' clean; reviewer double-hyphen '--' is OCR artifact",
    355: "reviewer expands bare-number P Tebt anaphora; raw-as-written, Phase 4",
    356: "reviewer expands '*ib.* 7⁴⁶³'->'P Lille I. 7⁴⁶³' anaphora; raw-as-written, Phase 4",
    358: "reviewer 'Heb 3⁶' is the CONTRAST verse ('confined to Heb 3¹⁴ (contrast v. 6), 6³'); ἐάνπερ doesn't occur there; producer correct",
    363: "keep [1 Pet 5⁵]: ἐγκομβόομαι IS the 1 Pet 5:5 verb (fragment-fold cleaned separately)",
}

KEYING = {
    1341: ("δυσεντέριον", "G1420", "dysentería",
           "δυσεντέριον is the NT-attested neuter (Ac 28⁸, 'all the uncials have the neuter') of δυσεντερία G1420"),
    1378: ("ἐγκοπή", "G1464", "enkopḗ",
           "cross-ref stub 'See ἐκκοπή, ἐκκόπτω.'; doubled lemma 'ἐγκοπή, ἐγκόπτω' cleaned to primary noun ἐγκοπή G1464"),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = skipped = 0

    with con:
        for did, note in DECISIONS.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

        # ---- ἐγκομβόομαι fold-forward: move ἔγκλητος fragment 1377 -> 1376 ----
        moved = 0
        body = con.execute("SELECT body_markdown FROM entries WHERE id=1377").fetchone()
        ekl = con.execute("SELECT body_markdown FROM entries WHERE id=1376").fetchone()
        if body and ekl and "We have found no instance" in body["body_markdown"]:
            marker = "We have found no instance"
            i = body["body_markdown"].index(marker)
            fragment = body["body_markdown"][:i].strip()
            clean = body["body_markdown"][i:].strip()
            con.execute("UPDATE entries SET body_markdown=? WHERE id=1377", (clean,))
            con.execute("UPDATE entries SET body_markdown=? WHERE id=1376",
                        ((ekl["body_markdown"].rstrip() + " " + fragment).strip(),))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=362 AND resolution IS NULL",
                        ("parser glued p209 ἔγκλημα's truncated ἔγκλητος tail onto the front of ἐγκομβόομαι; moved it back to ἔγκλημα (1376), cleaned ἐγκομβόομαι (1377)",
                         "manual:body-fix", now))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=361 AND resolution IS NULL",
                        ("entry IS ἐγκομβόομαι (the headword) once the prepended ἔγκλητος fragment is moved out; lemma kept",
                         "manual:keep-producer", now))
            moved = 1

        # ---- keying fixes ----
        rekeyed = 0
        for eid, (lemma, strongs, translit, note) in KEYING.items():
            e = con.execute("SELECT lemma_greek, strongs FROM entries WHERE id=?", (eid,)).fetchone()
            if not e or e["strongs"] == strongs:
                continue
            con.execute("UPDATE entries SET lemma_greek=?, strongs=?, lemma_translit=? WHERE id=?",
                        (lemma, strongs, translit, eid))
            con.execute("""INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value,
                           resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)""",
                        (eid, "strongs", "NULL (unmatched)", strongs, note, "manual:strongs-fix", now))
            rekeyed += 1

        # ---- ἔγγιστα G_N/A tombstone (non-NT superlative; stop phase3 re-attempts) ----
        tomb = 0
        e = con.execute("SELECT strongs FROM entries WHERE id=1367").fetchone()
        if e and e["strongs"] is None:
            exists = con.execute("SELECT 1 FROM disagreements WHERE entry_id=1367 AND field='strongs' AND resolution_by='manual:strongs-fix'").fetchone()
            if not exists:
                con.execute("""INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value,
                               resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)""",
                            (1367, "strongs", "NULL", "G_N/A",
                             "ἔγγιστα is the superlative adverb of ἐγγύς; not an NT lemma (NT: ἐγγύς G1451 / ἐγγύτερον G1452). Deliberate G_N/A.",
                             "manual:strongs-fix", now))
                tomb = 1

    print(f"\napplied (keep-producer): {applied}")
    print(f"ἐγκομβόομαι fold move:   {moved}")
    print(f"keying fixes:            {rekeyed} (δυσεντέριον->G1420, ἐγκοπή->G1464)")
    print(f"ἔγγιστα G_N/A tombstone: {tomb}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
