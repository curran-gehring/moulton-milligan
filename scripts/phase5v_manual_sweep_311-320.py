"""Phase 5v: one-shot manual sweep of residual disagreements for wave AB.

Pages 311-320 (end of Η: ἡσυχ-/ἤτοι/ἡττάομαι/ἦχος → into Θ: θάλασσα→θήκη, incl. the
big θεός entry spanning 317-318). THE LAST WAVE WITH VISION OCR READY (pages 321-735
need Phase 1B vision OCR before parsing). Mirrors phase5b-u. Phase-2 audit 92.1%
agree+minor (comfortably above gate — the Θ section parses cleanly). phase5_resolve.py
auto-closed 6 (5 continuation + 1 producer-superset). This script handles the residual 4
+ 1 reachability re-key.

Phase-3 keying: 58 exact + 3 snaps + 2 unmatched + 1 relabel. No snap-audit (all 3 snaps
handled manually): Ἡρῴδης→G2264 KEEP (ῴ/ώ accent), θανατηφόρος→G2287 KEEP (accent);
⚠️ ἡττάομαι re-keyed G2932→G2274 — the snap to κτάομαι (acquire) was a wrong coincidence;
ἡττάομαι (be defeated, 2 Pet 2:19) = ἡττάω/ἡσσάομαι G2274. 2 unmatched → G_N/A:
ἡμιλίτριον (half-pound, not NT; NT word is λίτρα G3046), θεολόγος (a Revelation TITLE in
certain MSS, not NT text). Relabel: id 2182 θεός→θεοδίδακτος G2312 (continuation of p316
θεοδίδακτος — its tail 'For the similarly formed Christian θεόγνωστος we can' flows into
p317 'now cite a pagan parallel…θεογνώστῳ'; parser mislabeled θεός).

reachability re-key (1):
  θέμα (p316, was G7651 extended): MM prints the headword 'θέμα = θεμέλιος' and the body is
    entirely about τὸ θεμέλιον (foundation, 1 Cor 3:11 etc.) — re-key to G2310 (θεμέλιος,
    NT) so the entry is reachable from the foundation verses. No separate θεμέλιος MM
    headword exists (θεμελιόω verb is G2311). Same reachability-override pattern as
    ἐπικέλλω→G2027 / Ζμύρνα→G4667 / Εὐρακύλων→G2148.

relabel-resolve (1):
  d#648 θεοδίδακτος lemma: reviewer said 'θεογνώστος', but θεόγνωστος is only DISCUSSED
    within p316's θεοδίδακτος entry ('For the similarly formed Christian θεόγνωστος…'), not
    a separate headword; my Phase-3 relabel θεός→θεοδίδακτος (the continuing headword) stands.

keep_producer (3):
  d#643 Ἡρῴδης body: producer correctly REMOVED the OCR artifact '(?between-tags)';
    reviewer wants to keep it. Keep producer.
  d#646 θέμα lemma: clean lemma 'θέμα'; reviewer wants the full 'θέμα = θεμέλιος' headword —
    the '= θεμέλιος' equivalence belongs in the body. Keep producer.
  d#647 θέμα body: producer keeps the 'θέμα = θεμέλιος.' equivalence marker at body head
    (legit MM content); keep producer.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"
INDEX_PATH = ROOT / "reference" / "strongs_lemma_index.json"

KEEP: dict[int, str] = {
    643: "producer correctly removed OCR artifact '(?between-tags)'; reviewer wants to keep it; keep producer",
    646: "clean lemma 'θέμα'; '= θεμέλιος' equivalence belongs in body, not the lemma; keep producer",
    647: "producer keeps 'θέμα = θεμέλιος.' equivalence marker at body head (legit MM content); keep producer",
}


def main() -> int:
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    rekeyed = resolved = applied = skipped = 0

    with con:
        # ---- reachability re-key: θέμα G7651 -> G2310 (θεμέλιος) ----
        e = con.execute("SELECT id, strongs FROM entries WHERE page_no=316 AND lemma_greek='θέμα'").fetchone()
        if e and e["strongs"] == "G7651":
            con.execute("UPDATE entries SET strongs=?, lemma_translit=? WHERE id=?",
                        ("G2310", idx.get("G2310", {}).get("translit"), e["id"]))
            con.execute("INSERT INTO disagreements (entry_id,field,producer_value,reviewer_value,"
                        "resolution,resolution_by,resolved_at) VALUES (?,?,?,?,?,?,?)",
                        (e["id"], "strongs", "G7651 (θέμα, extended)", "G2310 (θεμέλιος)",
                         "MM headword 'θέμα = θεμέλιος'; body entirely about τὸ θεμέλιον (1 Cor 3:11 etc.); "
                         "re-key to G2310 for NT reachability (no separate θεμέλιος MM headword exists)",
                         "manual:strongs-fix", now))
            rekeyed = 1

        # ---- relabel-resolve d#648 ----
        r = con.execute("SELECT resolution FROM disagreements WHERE id=648").fetchone()
        if r and r["resolution"] is None:
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=648 AND resolution IS NULL",
                        ("relabeled θεός→θεοδίδακτος (G2316→G2312) in Phase 3: continuation of p316 θεοδίδακτος; "
                         "reviewer's 'θεογνώστος' is discussed WITHIN that entry, not a separate headword",
                         "manual:lemma-fix", now))
            resolved += 1

        # ---- keep-producer ----
        for did, note in KEEP.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

    print(f"\nreachability re-key (θέμα→G2310): {rekeyed}")
    print(f"relabel-resolve: {resolved}")
    print(f"keep-producer: {applied}")
    print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
