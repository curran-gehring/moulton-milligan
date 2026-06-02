"""Phase 5x: one-shot manual sweep of residual disagreements for wave AD.

Pages 331-340 (book 301-310): ἱερ- group → Ἰησοῦς/Ἰουδαῖος/ἵστημι/ἰχθύς →
into Κ (κἀγώ→καθάπερ). Phase-2 audit 81.3% agree+minor (below gate, NON-systemic:
continuation-heavy ι/κ stretch — every preposition/long entry spans pages; +
reviewer-superset citation noise; lesson #1 = no prompt-refine). phase5_resolve.py
auto-closed 18 (6 continuation + 4 has-translation + 4 producer-superset +
4 reviewer-superset). This script CORRECTS the 4 reviewer-superset adds (literary/
journal refs -> body) and resolves the 3 skipped.

OCR REPAIR this wave: page 333 vision OCR DROPPED the '## ἱλασμός.' headword,
merging its one-sentence body ('On the formation of...substantives in -μός, see
Hatzidakis...') into ἱλάσκομαι. Restored the heading (ἱλασμός = propitiation,
1 Jn 2:2/4:10, G2434) + re-synced DB ocr_text + re-parsed p333 (7 entries).

Phase-3 keying: 67 exact + 5 snaps + 3 NULL. NULL manual keys: ἵστημι (ἱστάνω)
->G2476 (p337 head + p338 cont; index stores plain 'ἵστημι', MM headword carries
the ἱστάνω byform string so exact-match missed), Ἰωάννης, Ἰωάνης ->G2491. Snaps:
KEEP Ἰούνιᾶς->G2458 (accent/OCR), Ἰσραηλείτης->G2475 (ει/ι itacism); BAD snaps
re-keyed: ἶσος->G2470 (snap to σός G4674 wrong-stem; ἴσος 'equal'), Ἰτουραῖος
->G2484 (snap to Ἰουδαῖος G2453 wrong; Ituraea Lk 3:1 — reachability key, index
lemma is region Ἰτουραΐα; snap-audit dry-run REJECTed on noun/adj pedantry but
the NT verse slot is G2484, so protected as manual:strongs-fix — do NOT apply-run
the snap-audit), Ἰωνάθας->G_N/A (snap to Ἰωάθαμ G2488 wrong; Ἰωνάθας is the
Codex-D variant reading at Ac 4:6 — main text Ἰωάννης — with no own Strong's,
otherwise papyri-only). No homograph changes (2 ἵνα both confirmed G2443).

revert-reviewer-superset (4) — literary/journal refs the policy can't distinguish
from documentary papyri; revert entry.papyri_citations to producer (the refs
remain in body_markdown, so nothing is lost; Phase 4 does final extraction):
  d#681 ἱερόσυλος: '*Menandrea*' (Menander, literary) + bare 'p. 385³²'.
  d#688 Ἰουδαῖος: '*Hermes*' + Wilcken '*Archiv*' (scholarly journals) mixed in.
  d#689 Ἰσαάκ: bare anaphor '*ib.* p. 189'.
  d#694 ἰσχυρός: '*Menandrea* p. 141⁹' (Menander, literary).

keep-producer (3):
  d#682 ἱερόσυλος nt_refs: reviewer adds 'Rom 2²²' — but Rom 2:22 is ἱεροσυλεῖς,
    the cognate VERB ἱεροσυλέω (a separate p331 headword), not the noun ἱερόσυλος
    (whose NT ref is Ac 19:37). Keep producer ['Ac 19³⁷'].
  d#691 ἵστημι papyri: 'l. 11' citation-grouping granularity (Phase 4 normalizes).
  d#692 ἵστημι lemma: producer 'ἵστημι (ἱστάνω)' vs reviewer 'ἵστημι' — keep the
    byform string for Phase-6 dedup consistency with the p337 head (both G2476).
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

REVERT_SUPERSET = {
    681: "Menandrea (Menander, literary) + bare 'p. 385³²' -> body; revert to producer",
    688: "Hermes + Wilcken Archiv (scholarly journals) mixed in -> body; revert to producer",
    689: "bare anaphor 'ib. p. 189' -> body; revert to producer",
    694: "Menandrea (Menander, literary) -> body; revert to producer",
}

KEEP_PRODUCER = {
    682: "reviewer 'Rom 2²²' is ἱεροσυλεῖς (verb ἱεροσυλέω, separate p331 headword), not the noun ἱερόσυλος; keep producer ['Ac 19³⁷']",
    691: "'l. 11' citation-grouping granularity (Phase 4 normalizes); keep producer",
    692: "producer 'ἵστημι (ἱστάνω)' vs reviewer 'ἵστημι' — keep byform string for Phase-6 dedup with p337 head (both G2476)",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    reverted = kept = skipped = 0

    with con:
        for did, note in REVERT_SUPERSET.items():
            d = con.execute("SELECT entry_id, producer_value FROM disagreements WHERE id=?", (did,)).fetchone()
            if not d:
                skipped += 1
                continue
            con.execute("UPDATE entries SET papyri_citations=? WHERE id=?", (d["producer_value"], d["entry_id"]))
            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=?",
                (note, "manual:keep-producer (literary/journal -> body)", now, did),
            )
            reverted += 1

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

    print(f"revert reviewer-superset (literary/journal -> body): {reverted}")
    print(f"keep-producer: {kept}")
    print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
