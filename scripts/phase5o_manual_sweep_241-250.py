"""Phase 5o: one-shot manual sweep of residual disagreements for wave U.

Pages 241-250 (ἐν- compounds + start of ἐξ-). Mirrors phase5b-n. Phase-2 audit
84.6% agree+minor — marginally below the 85% gate, NON-systemic (lesson #1: no
prompt-refine). The dip is the continuation-heavy ἐν- stretch (6 of 10 pages open
mid-entry) plus citation anaphora. phase5_resolve.py auto-closed 10 (7 continuation
+ 1 has-translation-from-body ἐνδό(-ώ-)μησις + 2 legit Syll superset adds: ἐνδημέω
Syll 925²⁷, ἐνεργέω Syll 540¹⁹⁸). This script handles the residual 9 + 1 relabel.

Phase-3 keying: 78 exact + 10 fuzzy snaps + 3 unmatched. Snap-audit KEEP all 9 clean
νκ/γκ-assimilation + ν-doubling snaps (ἔνατος/ἐννατος, ἐνεός/ἐννεός, ἐνκαινίζω→
ἐγκαινίζω, ἐνκακέω→ἐκκακέω, ἐνκαυχάομαι, ἐνκεντρίζω, ἐνκοπή→ἐγκοπή [legit νκ/γκ here,
unlike wave-S ἐκκοπή↛ἐγκοπή which was a wrong-prefix reject], ἐνκρίνω, ἔνκυος). The
10th snap was a BAD snap caught pre-audit: ἐνορκίζω→G1844 (ἐξορκίζω) is a WRONG-prefix
coincidence (ἐν- vs ἐξ-); ἐνορκίζω (1 Th 5:27) = ἐνορκίζομαι G6034 (no classic id in
index). Manually re-keyed id 1665 → G6034 in Phase 3.

3 unmatched manually keyed in Phase 3: ἐνδό(-ώ-)μησις→G1739 (Rev 21:18; ο/ω variant
marker blocked match), ἕνεκα/ἕνεκεν/εἵνεκεν→G1752 (3-form headword), ἐντρέφομαι→G1789
(1 Tim 4:6, mid/pass of ἐντρέφω).

relabel (1):
  id 1666 (p247 pos 1): parser invented headword 'ἐξορκίζω' for what is actually the
    CONTINUATION TAIL of p246's ἐνορκίζω entry (id 1665). MM gives ἐξορκίζω NO own
    headword — its body opens mid-sentence ("V. iv. 31 (iii/A.D.) ἐξορκίζω σε...")
    continuing p246's closing cross-ref "For ἐξορκίζω see P Leid [W] V. iv. 31...",
    then discusses ἐνορκέω/ἔνορκος. Codex flagged it continuation. Relabel
    ἐξορκίζω→ἐνορκίζω, re-key G1844→G6034, so Phase-6 longest-body-wins folds it into
    id 1665. (Consequence: FirstWord MM has no standalone ἐξορκίζω/G1844 entry — faithful
    to MM, which doesn't separately treat it.)

adopt_reviewer (2):
  d#463 ἐνενήκοντα: detached 'Ostr 1511⁵·⁸' fragment ('1511⁵·⁸' → 'Ostr 1511⁵·⁸',
    Ostr prefix carried from the prior 'Ostr 1508⁵') — adopt reconstruction.
  d#474 ἐντός: detached 'BGU II. 611¹·⁶' fragment ('611¹·⁶' → 'BGU II. 611¹·⁶',
    BGU II. prefix carried from the prior 'BGU II. 378²⁵') — adopt reconstruction.

keep_producer (7):
  d#457 ἐνάρχομαι: reviewer reconstructs cf.⁵⁶ → 'P Tebt I. 24⁵⁶' (reasonable) BUT also
    adds 'Vett. Val. p. 212⁷⁵' — Vettius Valens is a CLASSICAL AUTHOR (belongs in body,
    not papyri_citations; wave-S footgun). Keep producer; the cf.⁵⁶ anaphora is Phase 4.
  d#459 ἔνδικος: reviewer adds line 'ⁱⁱ·²³' to 'Michel 1333'; Phase 4 normalizes.
  d#461 ἔνδοξος: reviewer adds editorial '(= III. p. 216)' to P Lond 1178²⁴; Phase 4.
  d#469 ἔντευξις: reviewer adds editorial gloss '(to Cleopatra III...)' to P Fay 12²⁶.
  d#470 ἔντιμος: Preisigke 424 + Syll 837 ARE present, prose-embedded in the body
    (the cf-list narrative + a standalone Syll-837 sentence); producer kept the
    structured cf-list, leaves prose citations for Phase 4 extraction. Not data loss.
  d#471 ἔντιμος nt_refs: '1 Pet 2⁴·⁶' (raised dot) vs '1 Pet 2⁴.⁶' (period) — trivial.
  d#472 ἐντολή: reviewer adds editorial gloss '(the letter of an official—c. A.D. 104)'.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

KEEP: dict[int, str] = {
    457: "reviewer adds classical author 'Vett. Val. p. 212⁷⁵' (belongs in body, not citations); cf.⁵⁶ anaphora is Phase 4",
    459: "reviewer adds line ref 'ⁱⁱ·²³' to Michel 1333; Phase 4 normalizes",
    461: "reviewer adds editorial '(= III. p. 216)' to P Lond 1178²⁴; Phase 4",
    469: "reviewer adds editorial gloss '(to Cleopatra III...)' to P Fay 12²⁶; raw-as-written, Phase 4",
    470: "Preisigke 424 + Syll 837 are prose-embedded in body; producer kept structured cf-list; Phase 4 extracts prose citations",
    471: "'1 Pet 2⁴·⁶' raised-dot vs '1 Pet 2⁴.⁶' period — trivial separator",
    472: "reviewer adds editorial gloss '(the letter of an official—c. A.D. 104)' to P Ryl I. 81³; Phase 4",
}

ADOPT = {463: 1636, 474: 1680}  # disagreement id -> entry id (citation reconstruction)


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = adopted = skipped = relabeled = 0

    with con:
        # ---- relabel id 1666: ἐξορκίζω -> ἐνορκίζω (continuation tail of p246 id 1665) ----
        cur = con.execute("SELECT lemma_greek, strongs FROM entries WHERE id=1666").fetchone()
        if cur and cur["lemma_greek"] == "ἐξορκίζω":
            con.execute(
                "UPDATE entries SET lemma_greek=?, strongs=?, lemma_translit=? WHERE id=1666",
                ("ἐνορκίζω", "G6034", "enorkizomai"),
            )
            con.execute(
                """INSERT INTO disagreements (entry_id,field,producer_value,reviewer_value,
                   resolution,resolution_by,resolved_at) VALUES (?,?,?,?,?,?,?)""",
                (1666, "lemma_greek", "ἐξορκίζω (G1844, parser-invented headword)",
                 "ἐνορκίζω (G6034)",
                 "continuation tail of p246 ἐνορκίζω (id 1665); MM gives ἐξορκίζω no own headword. "
                 "Relabel + re-key G1844->G6034; Phase-6 longest-body-wins folds into id 1665.",
                 "manual:lemma-fix", now),
            )
            relabeled = 1

        # ---- keep-producer residuals ----
        for did, note in KEEP.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

        # ---- adopt-reviewer: citation reconstructions ----
        for did, eid in ADOPT.items():
            row = con.execute("SELECT resolution, reviewer_value FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            new_cits = json.loads(row["reviewer_value"])
            con.execute("UPDATE entries SET papyri_citations=? WHERE id=?",
                        (json.dumps(new_cits, ensure_ascii=False), eid))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL",
                        ("adopted reviewer's detached-fragment citation reconstruction (prior-prefix carried)",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

    print(f"\nrelabeled (ἐξορκίζω->ἐνορκίζω): {relabeled}")
    print(f"applied (keep-producer): {applied}")
    print(f"applied (adopt-reviewer): {adopted}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
