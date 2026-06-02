"""Phase 5r: one-shot manual sweep of residual disagreements for wave X.

Pages 271-280 (ἐπι- compounds, ἐπιλανθάνομαι→ἐπιχειρέω). Mirrors phase5b-q. Phase-2
audit 85.1% agree+minor (just above gate). phase5_resolve.py auto-closed 11 (6
continuation + 2 has-translation + 3 citation superset/keeps). This script handles the
residual 5 (4 keep-producer + 1 body fragment-move).

Phase-3 keying: 69 exact + 2 snaps + 3 unmatched + 1 homograph. Snap-audit (dry-run,
NOT applied — protecting prior keeps per the wave-W non-determinism lesson): ἐπιρίπτω→
G1977 KEEP (ρ/ῤῥ variant, 1 Pet 5:7) promoted to manual:strongs-fix; ἐπιλείχω→G1952
REJECT enacted → G_N/A (ἐπιλείχω 'lick' Lk 16:21 WH ≠ ἐπιλείπω 'fail' G1952; ἐπιλείχω
not in index, critical-text variant). 3 unmatched: ἐπιμελέομαι→G1959 (Lk 10:34f), ἐπὶ
τὸ αὐτό→G_N/A (phrase, cross-ref to ἐπί), ἐπιτροπεύω→G_N/A (Lk 3:1 D variant, not NT
text). Homograph: ἐπίστασις→G1999 (classic over extended G20447; G1999 ἐπισύστασις is
the 2 Cor 11:28 ἐπίστασις/ἐπισύστασις variant pair).

body fragment-move (1):
  d#555 ἐπιφάνεια (id 1916, p280): the entry body wrongly PREPENDS the continuation
    TAIL of p279's ἐπιφαίνω entry (id 1915, cut off mid-Asclepieum-quote 'ἐπιφανέντα').
    Reviewer: the ἐπιφάνεια body 'should begin: The NT usage of this word to denote
    "manifestation"...'. Split id 1916's body at that marker; move the prefix (the
    temple-vision quote ending '...was healed.') to the end of id 1915 (ἐπιφαίνω).

keep_producer (4):
  d#541 ἐπιμένω nt_refs: 'Jn 8⁷' vs reviewer '[Jn] 8⁷' — the bracket marks the pericope
    adulterae; bare verse ref links correctly in FirstWord, keep producer.
  d#542 ἐπιορκέω lemma: clean 'ἐπιορκέω' vs reviewer 'ἐπ[ιφ-]ιορκέω' — the [ιφ-] bracket
    is an editorial aspirated-variant marker (ἐφιορκέω); clean lemma keys G1964, marker
    belongs in body. Keep producer.
  d#552 ἐπιτιμάω nt_refs: producer [] vs reviewer ['Mk 8³⁰'] — MM cites it as 'Allen ad
    Mk 8³⁰' (a COMMENTARY pointer, not a primary usage citation); producer's exclusion is
    deliberate and defensible. Keep producer (Phase-4 can revisit).
  d#553 ἐπιτιμία nt_refs: producer ['2 Cor 2⁶'] vs reviewer adds 'Wisd 3¹⁰' — Wisdom is
    APOCRYPHA, barred from nt_references by the parser rules; producer correctly excluded
    it, reviewer is WRONG. Keep producer.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

SPLIT_MARKER = "The NT usage of this word"
EPIPHANEIA_ID = 1916   # p280 ἐπιφάνεια (G2015)
EPIPHAINO_ID = 1915    # p279 ἐπιφαίνω (G2014)

KEEP: dict[int, str] = {
    541: "'Jn 8⁷' vs reviewer '[Jn] 8⁷' pericope-adulterae bracket; bare ref links, keep producer",
    542: "clean lemma ἐπιορκέω keys G1964; reviewer's 'ἐπ[ιφ-]ιορκέω' bracket is editorial aspirated-variant marker (body), keep producer",
    552: "reviewer's 'Mk 8³⁰' is cited as 'Allen ad Mk 8³⁰' (commentary pointer, not primary usage); producer's exclusion deliberate, keep producer",
    553: "reviewer adds 'Wisd 3¹⁰' = Wisdom (APOCRYPHA), barred from nt_references; producer correctly excluded it, keep producer",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = moved = skipped = 0

    with con:
        # ---- body fragment-move: d#555 ----
        row = con.execute("SELECT resolution FROM disagreements WHERE id=555").fetchone()
        if row and row["resolution"] is None:
            ep = con.execute("SELECT body_markdown FROM entries WHERE id=?", (EPIPHANEIA_ID,)).fetchone()
            body = ep["body_markdown"] or ""
            idx = body.find(SPLIT_MARKER)
            if idx <= 0:
                print(f"  d#555: split marker not found at a positive offset (idx={idx}); SKIP")
            else:
                prefix = body[:idx].strip()
                remainder = body[idx:].lstrip()
                fn = con.execute("SELECT body_markdown FROM entries WHERE id=?", (EPIPHAINO_ID,)).fetchone()
                fn_body = (fn["body_markdown"] or "").rstrip()
                con.execute("UPDATE entries SET body_markdown=? WHERE id=?",
                            (fn_body + " " + prefix, EPIPHAINO_ID))
                con.execute("UPDATE entries SET body_markdown=? WHERE id=?",
                            (remainder, EPIPHANEIA_ID))
                con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                            "WHERE id=555 AND resolution IS NULL",
                            (f"moved {len(prefix)}-char ἐπιφαίνω continuation tail (Asclepieum temple-vision quote) "
                             f"from ἐπιφάνεια id {EPIPHANEIA_ID} back to ἐπιφαίνω id {EPIPHAINO_ID}; "
                             f"ἐπιφάνεια now begins at '{SPLIT_MARKER}'",
                             "manual:fragment-move", now))
                moved = 1
        elif row:
            skipped += 1

        # ---- keep-producer ----
        for did, note in KEEP.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

    print(f"\nfragment-move: {moved}")
    print(f"applied (keep-producer): {applied}")
    print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
