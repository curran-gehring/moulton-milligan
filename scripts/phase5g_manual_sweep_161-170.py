"""Phase 5g: one-shot manual sweep of residual disagreements for wave M.

Pages 161-170 (end of Γ, start of Δ; parsed 2026-06-01). Mirrors phase5b-f.
phase5_resolve.py already auto-closed 9 (6 continuation-notes + 3
has_translation-from-body). This encodes the 8 manual residuals + 2 keying
fixes surfaced by the Phase-3 snap-audit.

Disagreements (8):
  keep_producer (raw-as-written / producer is the cleaner OCR):
    d#265 γραφικός body: producer "3 Macc 4²⁰" clean vs reviewer "4⁲⁰" garbled superscript
    d#267 γυμνασία body: invisible/whitespace diff; bodies identical in content
    d#277 δεκατόω body: reviewer injected a U+00AD soft-hyphen in τετραγωνίζω; producer clean
    d#270 δαιμόνιον papyri: bare "279¹"/"184" are *Syll* anaphora; Phase 4 expands
    d#273 δειγματίζω papyri: "28²⁸" vs chained "28²⁸, ⁷⁷"; raw-as-written, Phase 4 normalizes
  add (real content the producer dropped, verified in body):
    d#262 γράμμα papyri: body has "e.g. Rainer Pap. 215 in *Führer durch die
      Ausstellung* Tafel 9" — a named citation the producer omitted (lost data
      Phase 4 cannot recover). Append it.
    d#268 γυμνός nt: body "illustrate Luke's form of the Logion (6²⁹)" -> Luke 6²⁹.
      Insert at index 1 (reviewer's position).
  modify (chained-reference book-prefix rule):
    d#271 δαιμόνιον nt: trailing "9¹" should carry its book ("Lk 4³⁵, 9¹"). Replace
      "9¹" -> "Lk 9¹".

Keying fixes (from Phase-3 snap-audit; NOT new disagreement rows):
  δείκνυμι (entry 1084): auto-snapped to ἐνδείκνυμι (G1731), Codex REJECTed
    (prefixed lexeme). But δείκνυμι IS the NT verb "to show" — the index carries
    it under its -ω present δεικνύω = G1166. Positive re-key to G1166. The
    snap-audit left a manual:strongs-fix/'G_N/A' tombstone (d#283); update it to
    record the real key so it isn't misread as a non-NT word.
  δεῖνα (entry 1088): unmatched because the parser folded the article/gender tags
    into the lemma ("δεῖνα, ὁ, ἡ, τό"). Clean the lemma to "δεῖνα" and key G1170
    (the NT indefinite pronoun, Mt 26:18). Write a manual:strongs-fix row.

  (γραφικός 1049 + δεκανός 1099 stay NULL -> G_N/A: genuinely non-NT words;
   their snap-audit G_N/A tombstones are correct, left untouched.)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

# did -> (kind, *args)
DECISIONS: dict[int, tuple] = {
    265: ("keep_producer", "producer '3 Macc 4²⁰' clean; reviewer '4⁲⁰' garbled superscript"),
    267: ("keep_producer", "whitespace/invisible-char diff only; body content identical"),
    277: ("keep_producer", "reviewer injected U+00AD soft-hyphen in τετραγωνίζω; producer clean"),
    270: ("keep_producer", "bare '279¹'/'184' are *Syll* anaphora; raw-as-written, Phase 4 expands"),
    273: ("keep_producer", "'28²⁸' vs chained '28²⁸, ⁷⁷'; raw-as-written, Phase 4 normalizes"),
    262: ("add_papyri", "Rainer Pap. 215 in *Führer durch die Ausstellung* Tafel 9", None,
          "named citation in body ('e.g. Rainer Pap. 215 in ...') the producer dropped"),
    268: ("add_nt_ref", "Luke 6²⁹", 1,
          "body: \"illustrate Luke's form of the Logion (6²⁹)\" = Luke 6:29, attested"),
    271: ("replace_nt_ref", "9¹", "Lk 9¹",
          "chained-ref rule: 'Lk 4³⁵, 9¹' -> trailing 9¹ carries the Lk book prefix"),
}

# entry_id -> (new_lemma_or_None, new_strongs, new_translit, note)
KEYING_FIXES = {
    1084: (None, "G1166", "deiknýō",
           "δείκνυμι = NT 'to show'; index carries it as -ω present δεικνύω (G1166). "
           "auto-snap to ἐνδείκνυμι (G1731) was Codex-REJECTed (prefixed lexeme); manual key."),
    1088: ("δεῖνα", "G1170", "deîna",
           "parser folded article tags into lemma ('δεῖνα, ὁ, ἡ, τό'); cleaned to δεῖνα, "
           "keyed G1170 (NT indefinite pronoun, Mt 26:18)."),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    nt_changed = 0
    papyri_added = 0
    rekeyed = 0
    skipped = 0

    with con:
        for did, decision in DECISIONS.items():
            row = con.execute(
                "SELECT entry_id, resolution FROM disagreements WHERE id=?", (did,)
            ).fetchone()
            if not row:
                print(f"  d#{did}: not found, skip")
                continue
            if row["resolution"] is not None:
                skipped += 1
                continue
            kind = decision[0]
            eid = row["entry_id"]

            if kind == "keep_producer":
                resolution, by = decision[1], "manual:keep-producer"
            elif kind == "add_papyri":
                cite, _, note = decision[1], decision[2], decision[3]
                er = con.execute("SELECT papyri_citations FROM entries WHERE id=?", (eid,)).fetchone()
                arr = json.loads(er["papyri_citations"] or "[]")
                if cite not in arr:
                    arr.append(cite)
                    con.execute("UPDATE entries SET papyri_citations=? WHERE id=?",
                                (json.dumps(arr, ensure_ascii=False), eid))
                    papyri_added += 1
                resolution, by = note, "manual:accept-reviewer"
            elif kind == "add_nt_ref":
                ref, idx, note = decision[1], decision[2], decision[3]
                er = con.execute("SELECT nt_references FROM entries WHERE id=?", (eid,)).fetchone()
                arr = json.loads(er["nt_references"] or "[]")
                if ref not in arr:
                    arr.insert(idx if idx is not None and idx < len(arr) else len(arr), ref)
                    con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                                (json.dumps(arr, ensure_ascii=False), eid))
                    nt_changed += 1
                resolution, by = note, "manual:accept-reviewer"
            elif kind == "replace_nt_ref":
                old, new, note = decision[1], decision[2], decision[3]
                er = con.execute("SELECT nt_references FROM entries WHERE id=?", (eid,)).fetchone()
                arr = json.loads(er["nt_references"] or "[]")
                if old in arr:
                    arr[arr.index(old)] = new
                    con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                                (json.dumps(arr, ensure_ascii=False), eid))
                    nt_changed += 1
                resolution, by = note, "manual:accept-reviewer"
            else:
                print(f"  d#{did}: unknown kind {kind!r}; skip")
                continue

            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                "WHERE id=? AND resolution IS NULL",
                (resolution, by, now, did),
            )
            applied += 1

        # --- keying fixes (snap-audit residue) ---
        for eid, (new_lemma, strongs, translit, note) in KEYING_FIXES.items():
            e = con.execute("SELECT lemma_greek, strongs FROM entries WHERE id=?", (eid,)).fetchone()
            if not e:
                print(f"  entry {eid}: not found, skip")
                continue
            if e["strongs"] == strongs and (new_lemma is None or e["lemma_greek"] == new_lemma):
                continue  # already applied (idempotent)
            if new_lemma is not None:
                con.execute("UPDATE entries SET lemma_greek=?, strongs=?, lemma_translit=? WHERE id=?",
                            (new_lemma, strongs, translit, eid))
            else:
                con.execute("UPDATE entries SET strongs=?, lemma_translit=? WHERE id=?",
                            (strongs, translit, eid))
            # record/refresh a manual:strongs-fix row carrying the REAL key (not G_N/A),
            # so the entry isn't misread as non-NT and (being non-NULL) phase3 skips it.
            existing = con.execute(
                "SELECT id FROM disagreements WHERE entry_id=? AND field='strongs' "
                "AND resolution_by='manual:strongs-fix'", (eid,)
            ).fetchone()
            if existing:
                con.execute(
                    "UPDATE disagreements SET reviewer_value=?, resolution=?, resolved_at=? WHERE id=?",
                    (strongs, note, now, existing["id"]),
                )
            else:
                con.execute(
                    """INSERT INTO disagreements
                       (entry_id, field, producer_value, reviewer_value,
                        resolution, resolution_by, resolved_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (eid, "strongs", "NULL (unmatched/rejected snap)", strongs,
                     note, "manual:strongs-fix", now),
                )
            rekeyed += 1

    print(f"\napplied (disagreements): {applied}")
    print(f"nt_references changed:   {nt_changed}")
    print(f"papyri added:            {papyri_added}")
    print(f"keying fixes:            {rekeyed} (δείκνυμι->G1166, δεῖνα->G1170)")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
