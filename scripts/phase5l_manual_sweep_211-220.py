"""Phase 5l: one-shot manual sweep of residual disagreements for wave R.

Pages 211-220 (dense Ε prepositions/function words: εἰ, εἰμί, εἰς, εἷς, ἐκ).
Mirrors phase5b-k. Audit 78.6% — LOWEST so far, but NON-systemic: 10 of 21
disagreements are continuation-notes (every preposition entry spans 2-3 pages),
plus citation anaphora; only one real content fix (a duplicate NT ref). Content
sound; lesson #1 = no prompt-refine. phase5_resolve auto-closed 14.

The function-word section produced an unusually high crop of unmatched/snapped
lemmas because the index stores the lexical-form headword, not every aorist/byform:

  εἶδον (1401): aorist of εἴδω; fuzzy-snapped to εἶδος G1491 (noun 'form'),
    Codex-REJECTed. Key G1492 (εἴδω).
  εἴωθα (1440): perfect of ἔθω ('be accustomed', Mt 27¹⁵ etc.); MM entry is "See
    ἔθω."; snap to νεχωθά rejected. Key G1486 (ἔθω).
  εἶπον (1418): aorist of ἔπω; lemma had the variant folded in ("εἶπον, (—πα)").
    Clean to εἶπον, key G2036 (ἔπω).
  εἰσκαλέομαι (1432): middle of εἰσκαλέω (Ac 10²³); index has the active. Key G1528.
  εἶτεν (1439): the -εν byform of εἶτα ('then'). Key G1534 (εἶτα).

  ἕδρασμα RELABEL (1388): p211 opens with the continuation of p210's truncated
    ἑδραίωμα entry (1 Tim 3¹⁵, G1477; body discusses its rendering 'firmamentum').
    The parser mislabeled the continuation "ἕδρασμα" (a cognate mentioned in the
    text) and it fuzzy-snapped to δίασμα (rejected). Relabel -> ἑδραίωμα, key G1477
    (merges with 1387 in Phase 6). Mislabeled-continuation pattern (cf. wave-N δέχομαι).

  (εἶ μήν 1399 stays G_N/A: the Heb 6¹⁴ asseverative particle, an orthographic
   variant of ἦ μήν; a two-word phrase headword with no single Strong's. Snap to
   εἰ μή 'except' G1508 was correctly rejected. Tombstone is right.)

Plain residuals:
  d#388 εἰσπηδάω: producer nt has a DUPLICATE ["Ac 16²⁹","Ac 16²⁹"]; dedupe to one.
  d#376/377 εἶδον: keep producer — lemma 'εἶδον' (keys G1492); the "(-δα)" εἶδα
    by-form marker is MM content and stays in the body, not folded into the lemma.
  d#379/380 εἴκοσι/εἰκών papyri + d#390 εἶτεν papyri: anaphora/date-annotation;
    raw-as-written, Phase 4. d#386 εἰσάγω body: italic *BGU* vs BGU; keep producer.
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
    376: "keep lemma 'εἶδον' (keys G1492); reviewer's 'εἶδον, (-δα)' folds the εἶδα by-form marker into the lemma",
    377: "the '(-δα).' εἶδα by-form note is MM content; keep in body, producer correct",
    379: "reviewer expands bare-number BGU/Grenf anaphora; raw-as-written, Phase 4",
    380: "reviewer expands bare-number anaphora; raw-as-written, Phase 4",
    386: "italic '*BGU*' vs 'BGU' formatting only; keep producer",
    390: "reviewer appends '(B.C. 91)' date annotation to Michel 694²⁹; keep raw, Phase 4",
}

# entry_id -> (new_lemma_or_None, strongs, translit, note, has_gna_tombstone)
KEYING = {
    1401: (None, "G1492", "eídō", "εἶδον = aorist of εἴδω G1492; snap to εἶδος G1491 (noun 'form') rejected", True),
    1440: (None, "G1486", "éthō", "εἴωθα = perfect of ἔθω G1486 ('See ἔθω.'); snap to νεχωθά rejected", True),
    1388: ("ἑδραίωμα", "G1477", "hedraíōma", "continuation of p210's ἑδραίωμα (1 Tim 3¹⁵, G1477) mislabeled 'ἕδρασμα'; snap to δίασμα rejected", True),
    1418: ("εἶπον", "G2036", "épō", "εἶπον = aorist of ἔπω G2036; lemma had variant 'εἶπον, (—πα)' folded in", False),
    1432: (None, "G1528", "eiskaléō", "εἰσκαλέομαι = middle of εἰσκαλέω G1528 (Ac 10²³); index has the active form", False),
    1439: (None, "G1534", "eîta", "εἶτεν = -εν byform of εἶτα G1534 ('then')", False),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = deduped = rekeyed = skipped = 0

    with con:
        # keep-producer
        for did, note in KEEP.items():
            row = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (note, "manual:keep-producer", now, did))
            applied += 1

        # d#388 dedupe εἰσπηδάω nt
        row = con.execute("SELECT entry_id, resolution FROM disagreements WHERE id=388").fetchone()
        if row and row["resolution"] is None:
            er = con.execute("SELECT nt_references FROM entries WHERE id=?", (row["entry_id"],)).fetchone()
            arr = json.loads(er["nt_references"] or "[]")
            seen, dedup = set(), []
            for x in arr:
                if x not in seen:
                    seen.add(x); dedup.append(x)
            if dedup != arr:
                con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                            (json.dumps(dedup, ensure_ascii=False), row["entry_id"]))
                deduped = 1
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=388 AND resolution IS NULL",
                        ("deduped repeated 'Ac 16²⁹' -> single reference", "manual:accept-reviewer", now))
            applied += 1

        # keying fixes
        for eid, (lemma, strongs, translit, note, has_tomb) in KEYING.items():
            e = con.execute("SELECT lemma_greek, strongs FROM entries WHERE id=?", (eid,)).fetchone()
            if not e or e["strongs"] == strongs:
                continue
            if lemma is not None:
                con.execute("UPDATE entries SET lemma_greek=?, strongs=?, lemma_translit=? WHERE id=?",
                            (lemma, strongs, translit, eid))
            else:
                con.execute("UPDATE entries SET strongs=?, lemma_translit=? WHERE id=?", (strongs, translit, eid))
            if has_tomb:
                t = con.execute("SELECT id FROM disagreements WHERE entry_id=? AND field='strongs' AND resolution_by='manual:strongs-fix'", (eid,)).fetchone()
                if t:
                    con.execute("UPDATE disagreements SET reviewer_value=?, resolution=?, resolved_at=? WHERE id=?",
                                (strongs, note, now, t["id"]))
                else:
                    con.execute("""INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value,
                                   resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)""",
                                (eid, "strongs", "NULL (rejected snap)", strongs, note, "manual:strongs-fix", now))
            else:
                con.execute("""INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value,
                               resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)""",
                            (eid, "strongs", "NULL (unmatched)", strongs, note, "manual:strongs-fix", now))
            rekeyed += 1

    print(f"\napplied (disagreements): {applied}")
    print(f"nt dedupe (εἰσπηδάω):    {deduped}")
    print(f"keying fixes:            {rekeyed} (εἶδον G1492, εἴωθα G1486, ἑδραίωμα G1477, εἶπον G2036, εἰσκαλέομαι G1528, εἶτεν G1534)")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
