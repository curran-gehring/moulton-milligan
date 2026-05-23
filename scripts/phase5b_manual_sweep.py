"""Phase 5b: one-shot sweep of the residual manual disagreements.

This is NOT a reusable resolver — it encodes the per-case decisions made
during a manual review of `out/disagreements_manual.tsv` on 2026-05-23.

For each open disagreement, applies the recorded decision:
- `apply_reviewer_value`: write reviewer's value to the entry, close with resolution
- `apply_inline`: a one-off mutation (e.g. replace a list element), close
- `keep_producer`: just close the disagreement with the given reason
- `keep_producer_flagged`: keep producer but ensure needs_review stays on

After running, follow with:
  python scripts/phase3_strongs.py    # re-keys entries whose lemma changed (strongs cleared)
  python scripts/phase6_export.py     # regenerates out/

Idempotent — only touches rows where `resolution IS NULL`.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

# Manual decisions per disagreement_id.
# Each tuple is (kind, *args) where kind is one of:
#   "apply_reviewer_value"  — set entries.{field_col} = reviewer_value (with optional translit re-key)
#   "lemma_swap"            — change lemma_greek + clear strongs+translit (phase3 re-keys)
#   "lemma_swap_with_refs"  — lemma swap PLUS update nt_references from given JSON list string
#   "list_replace"          — in entries.{field_col} JSON list, replace `old` with `new`
#   "keep_producer"         — close-only, no entry mutation
#   "keep_producer_flagged" — same as keep_producer, plus assert needs_review=1
DECISIONS: dict[int, tuple] = {
    # --- reviewer-wins (real corrections) ---
    43:  ("lemma_swap", "αἰσχρός", "p44 pos9 was αἰσχρός; body discusses αἰ]σχρά; p45 pos2 also αἰσχύνη confirms parser merged continuation"),
    53:  ("lemma_swap_with_refs", "ἅμα", '["1 Th 4¹⁷", "1 Th 5¹⁰", "Mt 13²⁹"]', "p54 pos8 was ἅμα; body discusses ἅμα-σύν construction; all NT refs use ἅμα"),
    56:  ("close_paired_with", 53, "closed by d#53 lemma swap to ἅμα (this nt_refs update applied as part of that swap)"),
    75:  ("list_replace", "papyri_citations", "1567 (A.D. 105)", "Ostr 1567 (A.D. 105)", "reviewer caught missing Ostr publication prefix; matches surrounding Ostr 1154 / Ostr 1399 series"),
    80:  ("lemma_swap", "ἀναιρέω", "p64 continuation entry; reviewer identified lemma cleanly"),
    90:  ("lemma_swap", "ἄνηθον", "p73 continuation entry; reviewer identified lemma cleanly"),
    103: ("lemma_swap", "ἀνυδρία", "p80 continuation entry; reviewer identified lemma cleanly"),
    92:  ("keep_producer_flagged", "producer's guess ἀνόητος matches p74 pos7 prior-page chain exactly; needs_review retained"),

    # --- keep-producer (38) ---
    # papyri formatting / OG/S normalization / italics / date strips / etc.
    17:  ("keep_producer", "date qualifier strip; raw-as-written preserved"),
    18:  ("keep_producer", "ib. prefix + date qualifier additions/strips; producer matches source"),
    19:  ("keep_producer", "date qualifier strip"),
    20:  ("keep_producer", "comma vs semicolon separator; producer matches source"),
    32:  ("keep_producer", "ib. prefix add; producer matches source"),
    34:  ("keep_producer", "reviewer adds external commentary (Canopus inscription, Antiochus Epiphanes); raw-as-written rule"),
    35:  ("keep_producer", "reviewer adds external commentary (Epidaurus, in dialect); raw-as-written rule"),
    36:  ("keep_producer", "reviewer adds external commentary (Elatea); raw-as-written rule"),
    38:  ("keep_producer", "auditor's alternate body wording; producer body matches source page"),
    39:  ("keep_producer", "reviewer drops citations and adds annotation; keep producer"),
    41:  ("keep_producer", "reviewer used corrupted superscript ⁳⁷; producer ²⁷ is correct"),
    42:  ("keep_producer", "reviewer used corrupted superscript ⁳⁷; producer ²⁷ is correct"),
    48:  ("keep_producer", "reviewer added Eph 5³³ (not actually in NT for ἀλλά); keep producer"),
    52:  ("keep_producer", "reviewer dropped citations; keep producer (raw-as-written)"),
    54:  ("keep_producer", "auditor alternate body wording; producer matches source"),
    58:  ("keep_producer", "OGIS is standard scholarly form; producer normalized OG/S correctly"),
    59:  ("keep_producer", "OGIS is standard scholarly form; producer normalized OG/S correctly"),
    60:  ("keep_producer", "italics on l./ib. — house style"),
    61:  ("keep_producer", "OGIS is standard scholarly form; producer normalized OG/S correctly"),
    62:  ("keep_producer", "OGIS is standard scholarly form; producer normalized OG/S correctly"),
    63:  ("keep_producer", "OGIS is standard scholarly form; producer normalized OG/S correctly"),
    64:  ("keep_producer", "OGIS is standard scholarly form; producer normalized OG/S correctly"),
    65:  ("keep_producer", "italicized titles — house style"),
    67:  ("keep_producer", "italicized title — house style"),
    68:  ("keep_producer", "italicized German title — house style"),
    69:  ("keep_producer", "italicized publication abbreviations — house style"),
    70:  ("keep_producer", "italicized Latin words — house style"),
    72:  ("keep_producer", "OGIS normalization; producer correct"),
    74:  ("keep_producer", "OGIS is standard scholarly form"),
    79:  ("keep_producer", "em-dash spacing difference; cosmetic"),
    81:  ("keep_producer", "reviewer added (i/B.C.) date guess; keep producer (raw-as-written)"),
    84:  ("keep_producer", "reviewer typo'd 'hiladelphus; producer Philadelphus is correct"),
    85:  ("keep_producer", "reviewer added 'meant to be literary'/'occult' commentary; keep producer"),
    94:  ("keep_producer", "reviewer collapsed CIG entries with annotation; keep producer (raw-as-written)"),
    95:  ("keep_producer", "reviewer added Syll prefix + (= III. p. 177); keep producer (raw-as-written)"),
    99:  ("keep_producer", "reviewer dropped bare '1 Jn' reference; keep producer (raw-as-written)"),
    40:  ("keep_producer", "reviewer added syllable hyphen in lemma; bare lemma is correct for downstream"),
    49:  ("keep_producer", "?? placeholder retained; continuation lemma not recoverable from this page"),
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
                "SELECT entry_id, field, producer_value, reviewer_value, resolution FROM disagreements WHERE id=?",
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
                resolution = f"lemma swapped to {new_lemma!r}; strongs cleared for re-keying. {reason}"
                resolution_by = "manual:lemma-swap"
                entry_mutations += 1

            elif kind == "lemma_swap_with_refs":
                new_lemma, new_refs_json, reason = decision[1], decision[2], decision[3]
                con.execute(
                    "UPDATE entries SET lemma_greek=?, strongs=NULL, lemma_translit=NULL, nt_references=? WHERE id=?",
                    (new_lemma, new_refs_json, entry_id),
                )
                resolution = f"lemma swapped to {new_lemma!r} + nt_references replaced; strongs cleared. {reason}"
                resolution_by = "manual:lemma-swap"
                entry_mutations += 1

            elif kind == "close_paired_with":
                paired_did, reason = decision[1], decision[2]
                resolution = reason
                resolution_by = f"manual:paired-with-d{paired_did}"

            elif kind == "list_replace":
                field_col, old, new, reason = decision[1], decision[2], decision[3], decision[4]
                cur = con.execute(
                    f"SELECT {field_col} FROM entries WHERE id=?", (entry_id,)
                ).fetchone()[0]
                cur_list = json.loads(cur or "[]")
                if old not in cur_list:
                    print(f"  d#{did}: WARNING — {old!r} not in current {field_col} for entry#{entry_id}; skipping mutation")
                    resolution = f"intended list_replace skipped (value not present); {reason}"
                    resolution_by = "manual:list-replace-noop"
                else:
                    new_list = [new if x == old else x for x in cur_list]
                    con.execute(
                        f"UPDATE entries SET {field_col}=? WHERE id=?",
                        (json.dumps(new_list, ensure_ascii=False), entry_id),
                    )
                    resolution = f"replaced {old!r} with {new!r} in {field_col}. {reason}"
                    resolution_by = "manual:list-replace"
                    entry_mutations += 1

            elif kind == "keep_producer":
                resolution = decision[1]
                resolution_by = "manual:keep-producer"

            elif kind == "keep_producer_flagged":
                resolution = decision[1]
                resolution_by = "manual:keep-producer-flagged"
                # ensure the entry stays in needs_review
                con.execute("UPDATE entries SET needs_review=1 WHERE id=?", (entry_id,))

            else:
                print(f"  d#{did}: unknown decision kind {kind!r}; skipping")
                continue

            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=?",
                (resolution, resolution_by, now, did),
            )
            applied += 1

    print(f"\napplied:                 {applied}")
    print(f"entry mutations:         {entry_mutations}")
    print(f"skipped already-resolved: {skipped_already_resolved}")
    print(f"\nNext: python scripts/phase3_strongs.py && python scripts/phase6_export.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
