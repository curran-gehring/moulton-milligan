"""Phase 5w: one-shot manual sweep of residual disagreements for wave AC.

Pages 321-330 (book 291-300): end of Θ (θήκη→θώραξ) → Ι (Ἰάειρος→Ἱεράπολις) →
start of ἱερ- group (ἱερατεία→ἱεροπρεπής). FIRST Phase-2 wave off the freshly
vision-OCR'd 321-360 batch (page 326 = blank leaf, excluded). Phase-2 audit 81.5%
agree+minor (below 85% gate, NON-systemic: continuation-heavy θ/ι stretch + the
reviewer-superset citation noise; lesson #1 = no prompt-refine). phase5_resolve.py
auto-closed 13 (3 continuation-note + 2 has-translation + 1 producer-superset +
7 reviewer-superset). This script CORRECTS 3 of those reviewer-superset adds (the
classical-author / Apocrypha / MS-catalog footgun) and resolves the 3 skipped.

Phase-3 keying: 64 exact + 1 snap (Ἰεζάβελ→G2403, ε/η proper-noun spelling
variant — snap-audit dry-run KEEP, 0 rejects DB-wide). No unsettled homographs.
Page 329 was re-OCR'd this wave: the first vision pass TRUNCATED the Ἱεράπολις
entry at '...προεδρίᾳ τῶν'; re-OCR restored its conclusion incl. NT refs
Col 4¹³ + Ac 16¹¹ (verified vs primary PDF text layer).

revert-reviewer-superset (3) — the auto:reviewer-superset-citations policy can't
tell a dropped papyrus/inscription from a classical-AUTHOR / Apocrypha / MS-catalog
ref that belongs in BODY (wave-S/U footgun). Reverting entry.papyri_citations to
the producer's original; the parser was RIGHT to omit these:
  d#664 θλῖψις: 'Catal. VIII. 3, 175, 5' + 'VII. 169, 12' = Catalogus Codicum
    Astrologorum (CCAG) comparanda that *Boll* quotes in prose; literary MS-catalog,
    not documentary papyri/epigraphic → body.
  d#665 θραύω: 'Vett. Val. p. 276⁷' (Vettius Valens = classical author) +
    'Judith 9¹⁰' (Apocrypha) + 'ib. 7⁹' (anaphor to those) — all in prose → body.
  d#672 ἴασις: 'Vett. Val. p. 190³⁰' (classical author) → body (producer orig = []).

KEPT (legit documentary/epigraphic adds, auto-resolution stands — NO action):
  d#666 θρέμμα (Paris papyrus), d#668 θρησκεία (Rainer papyrus published by Wessely),
  d#670 Θωμᾶς (Inscr. Mission de Phénicie), d#677 ἱεροπρεπής (Foucart Associations
  religieuses — epigraphic corpus).

keep-producer (2):
  d#669 θρίξ papyri: producer '14¹⁸' vs reviewer 'ib. 14¹⁸' — citation anaphora
    granularity; Phase 4 normalizes anaphora. Keep producer.
  d#674 ἱερατεία lemma: producer clean 'ἱερατεία' vs reviewer 'ἱερατεία(–τία)' —
    the (–τία) parenthetical variant marker belongs in body; clean lemma keys to
    G2405. Keep producer.

adopt-reviewer (1):
  d#676 ἱεράτευμα nt_refs: reviewer adds '1 Pet 2⁵' — body reads '...in 1 Pet 2⁹ :
    in ib.⁵ Hort ad l. gives good reason...' where ib.⁵ = 1 Pet 2⁵, a real NT ref
    attested in the body via anaphora. Adopt.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

# disagreement ids whose auto:reviewer-superset add was a classical-author/
# Apocrypha/MS-catalog ref -> revert entry.papyri_citations to producer original
REVERT_SUPERSET = {
    664: "Catal. (CCAG) astrological-MS comparanda Boll quotes in prose -> body, not papyri/epigraphic; parser was right to omit",
    665: "Vett. Val. (classical author) + Judith (Apocrypha) + ib. anaphor -> body; parser was right to omit",
    672: "Vett. Val. (classical author) -> body; producer original was [] and correct",
}

KEEP_PRODUCER = {
    669: "producer '14¹⁸' vs reviewer 'ib. 14¹⁸' — citation anaphora granularity (Phase 4 normalizes); keep producer",
    674: "clean lemma 'ἱερατεία' vs reviewer 'ἱερατεία(–τία)' — (–τία) variant marker belongs in body; clean lemma keys G2405; keep producer",
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    reverted = kept = adopted = skipped = 0

    with con:
        # ---- revert reviewer-superset adds that are classical/apocrypha/MS-catalog ----
        for did, note in REVERT_SUPERSET.items():
            d = con.execute(
                "SELECT entry_id, producer_value FROM disagreements WHERE id=?", (did,)
            ).fetchone()
            if not d:
                skipped += 1
                continue
            # producer_value is the original citation JSON array (as a string)
            con.execute(
                "UPDATE entries SET papyri_citations=? WHERE id=?",
                (d["producer_value"], d["entry_id"]),
            )
            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=?",
                (note, "manual:keep-producer (classical/apocrypha/MS-catalog -> body)", now, did),
            )
            reverted += 1

        # ---- keep-producer on the skipped non-citation diffs ----
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

        # ---- adopt-reviewer: ἱεράτευμα += 1 Pet 2⁵ (ib.⁵ in body) ----
        d = con.execute(
            "SELECT entry_id, reviewer_value FROM disagreements WHERE id=676"
        ).fetchone()
        if d:
            r = con.execute("SELECT resolution FROM disagreements WHERE id=676").fetchone()
            if r and r["resolution"] is None:
                con.execute(
                    "UPDATE entries SET nt_references=? WHERE id=?",
                    (d["reviewer_value"], d["entry_id"]),
                )
                con.execute(
                    "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=676 AND resolution IS NULL",
                    (
                        "adopt reviewer: body '...1 Pet 2⁹ : in ib.⁵ Hort ad l...' -> ib.⁵ = 1 Pet 2⁵, real NT ref via anaphora",
                        "manual:adopt-reviewer",
                        now,
                    ),
                )
                adopted += 1
            else:
                skipped += 1

    print(f"revert reviewer-superset (classical/apocrypha/MS-catalog -> body): {reverted}")
    print(f"keep-producer: {kept}")
    print(f"adopt-reviewer (ἱεράτευμα += 1 Pet 2⁵): {adopted}")
    print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
