"""Phase 5q: one-shot manual sweep of residual disagreements for wave W.

Pages 261-270 (ἐπ-/ἐπι- compounds, dominated by the 4-PAGE preposition ἐπί spanning
262-265). Mirrors phase5b-p. Phase-2 audit 84.6% agree+minor — marginally below the
85% gate, but NON-systemic: the ἐπί mega-entry makes pages 263 & 264 single-entry
continuation fragments that are 100% 'major' by construction (same function-word
pattern as wave-R εἰ/εἰμί). Lesson #1: no prompt-refine. phase5_resolve.py auto-closed
11 (6 continuation + 2 has-translation + 3 producer-superset citation keeps). This
script handles the residual 4.

Phase-3 keying: 54 exact + 2 snaps + 2 unmatched. Snap-audit dry-run flagged 2 REJECTs,
BOTH handled WITHOUT applying the reject (the apply would have wrongly reverted them):
  - ἐπικέλλω→G2027 (p270): ἐπικέλλω is the WH/NA reading at Ac 27:41 (ἐπέκειλαν);
    ἐποκέλλω G2027 = the TR reading of the SAME verse. Codex flagged the κέλλω/ὀκέλλω
    root distinction, but the NT verse slot is G2027 — KEEP for reachability. Promoted
    to manual:strongs-fix G2027.
  - ἐνκακέω→G1573 (p245, WAVE U): Codex KEPT this twice in wave U then flipped to REJECT
    on re-audit — NON-DETERMINISM (cf. the wave-T homograph flip). ἐνκακέω/ἐγκακέω =
    ἐκκακέω G1573 (lose heart, Lk 18:1 etc.), the standard νκ/γκ + critical-vs-TR variant
    pair. Promoted to manual:strongs-fix G1573 to PROTECT the correct prior key. LESSON:
    the snap-audit re-judges ALL live snaps every run and Codex can flip a prior KEEP to
    REJECT; never run apply blindly — dry-run, and protect confirmed keeps by promoting
    to manual:strongs-fix.
The other BAD snap was caught pre-audit: ἐπεκτείνω→G1614 (ἐκτείνω) is wrong-prefix;
ἐπεκτείνομαι (Phil 3:13) = G1901 — manually re-keyed in Phase 3.

2 unmatched + 1 homograph resolved in Phase 3: ἐπικεφάλαιον→G_N/A (Mk 12:14 D Θ variant
for κῆνσον, not NT text); ἔπειμι id 1790→G7376 (homograph: ἔπειμι maps to extended
G7376+G7377 only, no classic id; Codex picked the be-upon/next-day sense G7376).

relabel (1):
  id 1817 (p267 pos 1): parser invented 'ἐπιθεωρέω' (from ἐπιθεωρησάντων in a quoted
    papyrus) but it's the CONTINUATION of p266's ἐπιγινώσκω entry (id 1816, G1921) —
    which lists 'ἐπι- compounds of the kind Dean Robinson describes' with papyrus
    examples. Codex flagged it (lemma → 'continuation from prior page'). Relabel
    →ἐπιγινώσκω, key NULL→G1921; Phase-6 longest-body-wins folds it into id 1816.

adopt_reviewer (1):
  d#526 ἐπιγινώσκω (id 1816): detached 'P Tebt II. 319^{11}' fragment ('319^{11}' →
    'P Tebt II. 319^{11}', prefix carried from prior 'P Tebt II. 297^{4}') — adopt the
    reviewer's reconstruction (clean 12-element array).

keep_producer (2):
  d#518 ἐπέρχομαι nt_refs: 'Lk 1⁸⁵' is OCR-garbled (no Lk 1:85) — likely Lk 1³⁵ or Ac 1⁸,
    but the reviewer's bare '1⁸' is no better; not confident enough to correct, leave for
    Phase-4 proofing against the page image. Keep producer.
  d#523 ἐπί nt_refs: producer and reviewer carry the SAME 12 refs, only reordered (Ac 1¹⁵
    / Ac 2⁴⁷ shifted) — set-identical, order immaterial. Keep producer.
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
    518: "'Lk 1⁸⁵' is OCR-garbled (no Lk 1:85); reviewer's bare '1⁸' no better — leave for Phase-4 proofing; keep producer",
    523: "producer & reviewer carry the same 12 ἐπί refs, only reordered — set-identical, keep producer",
}

ADOPT = {526: 1816}             # disagreement id -> entry id (citation reconstruction)
RELABEL = {527: (1817, "ἐπιγινώσκω", "G1921", "epiginṓskō")}  # did -> (eid, lemma, strongs, translit)


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = adopted = relabeled = skipped = 0

    with con:
        # ---- relabel ----
        for did, (eid, lemma, strongs, translit) in RELABEL.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row or row["resolution"] is not None:
                skipped += 1; continue
            cur = con.execute("SELECT lemma_greek, strongs FROM entries WHERE id=?", (eid,)).fetchone()
            con.execute("UPDATE entries SET lemma_greek=?, strongs=?, lemma_translit=? WHERE id=?",
                        (lemma, strongs, translit, eid))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL",
                        (f"relabel continuation tail: {cur['lemma_greek']}({cur['strongs']}) -> {lemma}({strongs}); "
                         f"parser-invented headword from a word inside a quoted papyrus; Phase-6 folds into the p266 entry",
                         "manual:lemma-fix", now, did))
            relabeled += 1

        # ---- adopt reviewer (citation reconstruction) ----
        for did, eid in ADOPT.items():
            row = con.execute("SELECT resolution, reviewer_value FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row or row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE entries SET papyri_citations=? WHERE id=?",
                        (json.dumps(json.loads(row["reviewer_value"]), ensure_ascii=False), eid))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL",
                        ("adopted reviewer's detached-fragment citation reconstruction (P Tebt II. 319 prefix carried)",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        # ---- keep-producer ----
        for did, note in KEEP.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row or row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

    print(f"\nrelabeled: {relabeled}")
    print(f"applied (adopt-reviewer): {adopted}")
    print(f"applied (keep-producer): {applied}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
