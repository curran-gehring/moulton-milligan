"""Phase 5d: one-shot manual sweep of residual disagreements for waves H+I.

Encodes per-case decisions for the disagreements left open by phase5_resolve.py
across pages 111-130 (parsed 2026-06-01). Mirrors phase5b/phase5c structure.

Decision kinds:
- "lemma_swap"        — change lemma_greek + clear strongs/translit + clear any
                        G_N/A tombstone (phase3 --from/--to re-keys the new lemma)
- "set_nt_references" — overwrite entries.nt_references with given JSON list string
- "body_replace"      — literal substring replace in entries.body_markdown (asserts
                        the old substring is present; no-op + warning if missing)
- "keep_producer"     — close-only, no entry mutation
- "keep_producer_flagged" — keep producer + assert needs_review=1

After running:
  python scripts/phase3_strongs.py --from 111 --to 130   # re-keys swapped lemmas
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

DECISIONS: dict[int, tuple] = {
    # --- reviewer-wins (real corrections, verified vs source pages) ---
    178: ("lemma_swap", "ἀρχι-",
          "p112 opens continuing the ἀρχι- prefix compound-list from p111 "
          "(ἀρχιπροφήτης, ἀρχιθυρωρός… are EXAMPLES within the ἀρχι- entry, not headwords). "
          "Parser wrongly split ἀρχιπροφήτης as its own headword. No NT Strong's (prefix)."),
    192: ("lemma_swap", "αὐτόπτης",
          "p124 opens continuing the αὐτόπτης entry from p123 (the αὐτοψία/αὐτοπτος "
          "discussion is inside αὐτόπτης, no ## heading). Parser invented an αὐτοψία headword."),
    195: ("set_nt_references", '["2 Peter"]',
          "p125 αὐχμηρός body: 'We can quote only verse parallels for this word of 2 Peter' "
          "— MM's sole NT ref (no verse on page; locus is 2 Pet 1:19). Parser left it empty."),
    201: ("body_replace", "occurs *fer* in the magic papyrus", "occurs *ter* in the magic papyrus",
          "p126 ἄφθαρτος: source reads *ter* ('three times'), parser/OCR produced *fer*."),

    # --- keep-producer-flagged (structural, content present but mis-attributed) ---
    194: ("keep_producer_flagged",
          "p125 αὐχμηρός body has the αὐχέω-continuation tail from p124 prepended "
          "('even in poetry!)… language of poetry.'). All content present but mis-located; "
          "splitting would lose the αὐχέω tail (no other home). Flag for a future re-parse."),

    # --- keep-producer: citation anaphora/shorthand = Phase 4 normalization ---
    196: ("keep_producer", "trailing bare line-refs continue the preceding Syll./ib. chain; Phase 4"),
    197: ("keep_producer", "Thebes 492² is a Kaibel/ib. anaphoric ref, not a bare standalone; Phase 4"),
    200: ("keep_producer", "'44 verso ii.¹⁸¹' is an *ib.* P Petr continuation; raw-as-written; Phase 4"),
    203: ("keep_producer", "'l. 27' / *al.* are anaphoric sub-refs of BGU II. 614; Phase 4 resolves"),
    204: ("keep_producer", "bare '47' is a P Lips I. 64 line-ref (anaphora); Phase 4 expands"),
    205: ("keep_producer", "last citation's source descriptor is anaphoric; whitespace-only else; Phase 4"),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    entry_mutations = 0
    skipped_already_resolved = 0

    with con:
        for did, decision in DECISIONS.items():
            row = con.execute(
                "SELECT entry_id, field, resolution FROM disagreements WHERE id=?",
                (did,),
            ).fetchone()
            if not row:
                print(f"  d#{did}: not found, skip")
                continue
            if row["resolution"] is not None:
                skipped_already_resolved += 1
                continue
            entry_id = row["entry_id"]
            kind = decision[0]

            if kind == "lemma_swap":
                new_lemma, reason = decision[1], decision[2]
                con.execute(
                    "UPDATE entries SET lemma_greek=?, strongs=NULL, lemma_translit=NULL WHERE id=?",
                    (new_lemma, entry_id),
                )
                con.execute(
                    "DELETE FROM disagreements WHERE entry_id=? "
                    "AND resolution_by='manual:strongs-fix' AND reviewer_value='G_N/A'",
                    (entry_id,),
                )
                resolution = f"lemma swapped to {new_lemma!r}; strongs cleared for re-keying. {reason}"
                resolution_by = "manual:lemma-swap"
                entry_mutations += 1

            elif kind == "set_nt_references":
                new_refs_json, reason = decision[1], decision[2]
                con.execute(
                    "UPDATE entries SET nt_references=? WHERE id=?", (new_refs_json, entry_id),
                )
                resolution = f"nt_references set to {new_refs_json}. {reason}"
                resolution_by = "manual:nt-refs-fix"
                entry_mutations += 1

            elif kind == "body_replace":
                old, new, reason = decision[1], decision[2], decision[3]
                cur = con.execute(
                    "SELECT body_markdown FROM entries WHERE id=?", (entry_id,)
                ).fetchone()[0] or ""
                if old not in cur:
                    print(f"  d#{did}: WARNING — {old!r} not in body for entry#{entry_id}; mutation skipped")
                    resolution = f"intended body_replace skipped (substring absent); {reason}"
                    resolution_by = "manual:body-replace-noop"
                else:
                    con.execute(
                        "UPDATE entries SET body_markdown=? WHERE id=?",
                        (cur.replace(old, new), entry_id),
                    )
                    resolution = f"body_replace {old!r}->{new!r}. {reason}"
                    resolution_by = "manual:body-replace"
                    entry_mutations += 1

            elif kind == "keep_producer":
                resolution = decision[1]
                resolution_by = "manual:keep-producer"

            elif kind == "keep_producer_flagged":
                resolution = decision[1]
                resolution_by = "manual:keep-producer-flagged"
                con.execute("UPDATE entries SET needs_review=1 WHERE id=?", (entry_id,))

            else:
                print(f"  d#{did}: unknown kind {kind!r}; skip")
                continue

            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                "WHERE id=? AND resolution IS NULL",
                (resolution, resolution_by, now, did),
            )
            applied += 1

    print(f"\napplied:                  {applied}")
    print(f"entry mutations:          {entry_mutations}")
    print(f"skipped already-resolved: {skipped_already_resolved}")
    print(f"\nNext: python scripts/phase3_strongs.py --from 111 --to 130")
    return 0


if __name__ == "__main__":
    sys.exit(main())
