"""Phase 5u: one-shot manual sweep of residual disagreements for wave AA.

Pages 301-310 (the short Ζ section ζάω→ζωοποιέω + start of Η: ἤ→ἥμισυς). Mirrors
phase5b-t. Two SPARSE pages this wave (p301 = a single ἕως continuation fragment;
p305 = ζώνη-tail + 3 entries) — Ζ is a short letter. Phase-2 audit 84.2% agree+minor
(marginally below gate, NON-systemic: with only 57 entries, the p301 single-continuation
auto-major + a couple of boundary-mislabels swing the %; lesson #1 no prompt-refine).
phase5_resolve.py auto-closed 9 (7 continuation + 1 has-translation + 1 producer-superset).
This script handles the residual 5.

Phase-3 keying: 52 exact + 3 snaps + 2 unmatched + 1 homograph; all 3 snaps handled
manually (no snap-audit run — nothing genuinely uncertain left): ζβέννυμι→G4570 KEEP
(ζβ/σβ Koine, Mt 12:20); Ζμύρνα re-keyed G4666→G4667 (the snap picked σμύρνα=myrrh, but
the entry is the CITY Σμύρνα, Rev 1:11 per body 'read by ℵ'); ἦ μήν→G_N/A (2-word Heb
6:14 affirmation phrase, consistent with wave-R εἶ μήν). 2 unmatched: Ἠλεί→G2241 (Mt
27:46), ἡμίωρον→G2256 (Rev 8:1). Homograph ζηλωτής pre-settled G2207 (common noun, body
1 Cor 14:12 / Ac 22:3 — NOT Simon the Zealot G2208).

relabel done in Phase 3 (resolve the audit's lemma disagreement here):
  d#621 id 2094 (p303): parser labeled 'ζηλόω' but it's the CONTINUATION of p302's ζῆλος
    (body: 'fervour rather than emulation as the primary idea of the word'). Relabeled
    →ζῆλος G2205; the real ζηλόω entry follows it on p303.

targeted body fix (1):
  d#619 ἕως (p301): OCR slip 'ausque ad primum' → 'usque ad primum' (Latin 'usque ad' =
    'up to'); a stray leading 'a'. Targeted string replace (don't wholesale-overwrite body).

keep_producer (3):
  d#623 ζημία citations: 'OGIS 218⁹⁹, 483³⁰' — producer keeps '483³⁰' as shared-OGIS-prefix
    anaphora; reviewer expands to 'OGIS 483³⁰'; Phase 4 normalizes anaphora.
  d#624 ζητέω body: in-quotation accent 'Ἄιδην' vs reviewer 'Ἀίδην' (Hades); trivial Greek
    accent diff in a papyrus quote, Phase-4 proofing territory, keep producer.
  d#627 ἤ nt_refs: producer & reviewer carry the SAME 8 refs, only reordered (Rom 6¹⁶
    moved to front); set-identical, keep producer.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

KEEP: dict[int, str] = {
    623: "producer keeps '483³⁰' as shared-OGIS-prefix anaphora; reviewer expands to 'OGIS 483³⁰'; Phase 4 normalizes",
    624: "in-quotation Greek accent 'Ἄιδην'/'Ἀίδην' (Hades); trivial, Phase-4 proofing, keep producer",
    627: "producer & reviewer carry the same 8 ἤ refs, only reordered (Rom 6¹⁶ to front); set-identical, keep producer",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    resolved = fixed = applied = skipped = 0

    with con:
        # ---- relabel-resolve d#621 (lemma already changed in Phase 3) ----
        r = con.execute("SELECT resolution FROM disagreements WHERE id=621").fetchone()
        if r and r["resolution"] is None:
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=621 AND resolution IS NULL",
                        ("lemma relabeled ζηλόω→ζῆλος (G2206→G2205) in Phase 3: continuation of p302 ζῆλος, not a ζηλόω headword",
                         "manual:lemma-fix", now))
            resolved += 1
        else:
            skipped += 1

        # ---- targeted body OCR fix d#619: 'ausque ad'→'usque ad' on the ἕως p301 entry ----
        rr = con.execute("SELECT resolution FROM disagreements WHERE id=619").fetchone()
        if rr and rr["resolution"] is None:
            e = con.execute("SELECT id, body_markdown FROM entries WHERE page_no=301 AND lemma_greek='ἕως'").fetchone()
            if e and "ausque ad" in (e["body_markdown"] or ""):
                con.execute("UPDATE entries SET body_markdown=? WHERE id=?",
                            (e["body_markdown"].replace("ausque ad", "usque ad"), e["id"]))
                con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=619 AND resolution IS NULL",
                            ("OCR slip fixed: 'ausque ad primum'→'usque ad primum' (Latin usque ad; stray leading a)",
                             "manual:adopt-reviewer", now))
                fixed += 1
            else:
                print("  d#619: 'ausque ad' not found in ἕως body; SKIP")

        # ---- keep-producer ----
        for did, note in KEEP.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

    print(f"\nrelabel-resolve: {resolved}")
    print(f"body OCR fix: {fixed}")
    print(f"keep-producer: {applied}")
    print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
