"""Phase 5i: one-shot manual sweep of residual disagreements for wave O.

Pages 181-190 (Δ section; parsed 2026-06-01). Mirrors phase5b-h.
phase5_resolve.py auto-closed 10 (continuation-notes + has_translation-from-body).
This encodes the 8 manual residuals + 3 keying fixes from the Phase-3 snap-audit.

Substantive fixes:
  διασπάω fragment MOVE (d#315). The parser folded the tail of p183's truncated
    διασπάω entry ("τοκιστοῦ μέρη μήτε τὰ τοῦ γεωργοῦ...") onto the FRONT of the
    p184 διασπείρω body. p183 ends "μὴ διασπῶντες μήτε τὰ τοῦ" -> the fragment is
    διασπάω's continuation. Move it: append the fragment to διασπάω (entry 1206)
    and strip it from διασπείρω (entry 1207). Preserves the content in the right
    entry (inverse of the wave-N δέσμη OCR-split, which had to MERGE).
  διαλύω RELABEL (d#311). p182 opens with the tail of p181's truncated διαλύω
    headword ("...ἐν τῷ Νόμῳ διαλύεται..."). Parser labeled it διαλύομαι (voice
    variant, not in index -> auto-snapped to διάλλομαι, Codex-REJECTed). Relabel
    entry 1187 -> διαλύω and key G1262 (the headword form).
  διάλεκτος nt add (d#307). Body cites "...'Sprache' in general (as Ac 2⁶)".
    Producer left nt empty; reviewer proposed "Ac 2³" — WRONG verse (Ac 2:3 is
    tongues of fire, not language). Add the correct "Ac 2⁶".

Keying fix (byform of an NT verb, same class as wave-M δείκνυμι->δεικνύω):
  διαλιμπάνω (entry 1182): the -λιμπάνω present byform of διαλείπω; not separately
    numbered in the index. Body cites Ac 8²² D*. Key G1257 (διαλείπω).

  (διαφορά entry 1231 stays NULL -> G_N/A: snap to διαφθορά G1312 Codex-REJECTed;
   διαφορά "difference" is not an NT lemma. Its G_N/A tombstone is correct.
   δίδυμος kept G1324 by the snap-audit: same lexeme, twin / the name Didymus.)

keep_producer (raw-as-written / producer is the cleaner OCR):
  d#306 διάλεκτος body: producer "Ac 2⁶" correct; reviewer "Ac 2³" wrong verse
  d#309 διαλογίζομαι body: producer "becomes" clean vs reviewer "hecomes" garble
  d#310 διαλύω papyri: bare "1²²"/"26⁹"/"38²⁸" are P Par anaphora; Phase 4 expands
  d#314 διασαφέω nt: reviewer wants bare "Mt" (no verse); the book mention stays
        in body as prose ("only one NT writer (Mt)"); not a usable nt_reference
  d#321 διαφυλάσσω body: producer "φιλοτιμότεροι" clean vs reviewer hyphenated
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

DECISIONS: dict[int, tuple] = {
    306: ("keep_producer", "producer 'Ac 2⁶' is the correct διάλεκτος verse; reviewer 'Ac 2³' (tongues of fire) is wrong"),
    309: ("keep_producer", "producer 'becomes' clean; reviewer 'hecomes' is OCR garble"),
    310: ("keep_producer", "bare '1²²'/'26⁹'/'38²⁸' are P Par anaphora; raw-as-written, Phase 4 expands"),
    314: ("keep_producer", "reviewer wants bare 'Mt' (no verse); book mention stays in body prose, not nt_references"),
    321: ("keep_producer", "producer 'φιλοτιμότεροι' clean; reviewer hyphen-split is OCR artifact"),
    307: ("add_nt_ref", "Ac 2⁶", None,
          "body: \"'Sprache' in general (as Ac 2⁶)\" -> Acts 2:6 (διάλεκτος); reviewer's 'Ac 2³' is the wrong verse"),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = nt_added = skipped = 0

    with con:
        for did, dec in DECISIONS.items():
            row = con.execute("SELECT entry_id, resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not row:
                print(f"  d#{did}: not found"); continue
            if row["resolution"] is not None:
                skipped += 1; continue
            kind = dec[0]; eid = row["entry_id"]
            if kind == "keep_producer":
                resolution, by = dec[1], "manual:keep-producer"
            elif kind == "add_nt_ref":
                ref, idx, note = dec[1], dec[2], dec[3]
                er = con.execute("SELECT nt_references FROM entries WHERE id=?", (eid,)).fetchone()
                arr = json.loads(er["nt_references"] or "[]")
                if ref not in arr:
                    arr.insert(idx if idx is not None and idx < len(arr) else len(arr), ref)
                    con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                                (json.dumps(arr, ensure_ascii=False), eid))
                    nt_added += 1
                resolution, by = note, "manual:accept-reviewer"
            else:
                print(f"  d#{did}: unknown kind"); continue
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                        "WHERE id=? AND resolution IS NULL", (resolution, by, now, did))
            applied += 1

        # ---- d#315: move διασπάω tail fragment from διασπείρω(1207) to διασπάω(1206) ----
        moved = 0
        sp = con.execute("SELECT body_markdown FROM entries WHERE id=1207").fetchone()
        spao = con.execute("SELECT body_markdown FROM entries WHERE id=1206").fetchone()
        if sp and spao and "The verb is found" in sp["body_markdown"]:
            marker = "The verb is found"
            i = sp["body_markdown"].index(marker)
            fragment = sp["body_markdown"][:i].strip()
            clean = sp["body_markdown"][i:].strip()
            con.execute("UPDATE entries SET body_markdown=? WHERE id=1207", (clean,))
            con.execute("UPDATE entries SET body_markdown=? WHERE id=1206",
                        ((spao["body_markdown"].rstrip() + " " + fragment).strip(),))
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=315 AND resolution IS NULL",
                        ("parser folded p183 διασπάω's truncated tail onto the front of διασπείρω; moved the fragment back to διασπάω (1206) and cleaned διασπείρω (1207)",
                         "manual:body-fix", now))
            moved = 1

        # ---- d#311: relabel διαλύομαι(1187) -> διαλύω, key G1262; refresh snap tombstone ----
        relabeled = 0
        e = con.execute("SELECT lemma_greek FROM entries WHERE id=1187").fetchone()
        if e and e["lemma_greek"] != "διαλύω":
            con.execute("UPDATE entries SET lemma_greek='διαλύω', strongs='G1262', lemma_translit='dialýō' WHERE id=1187")
            con.execute("UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? WHERE id=311 AND resolution IS NULL",
                        ("continuation of p181's truncated διαλύω headword; parser used voice-variant διαλύομαι (not in index). Relabeled + keyed G1262.",
                         "manual:lemma-swap", now))
            # refresh the snap-audit G_N/A tombstone to the real key
            t = con.execute("SELECT id FROM disagreements WHERE entry_id=1187 AND field='strongs' AND resolution_by='manual:strongs-fix'").fetchone()
            if t:
                con.execute("UPDATE disagreements SET reviewer_value='G1262', resolution=?, resolved_at=? WHERE id=?",
                            ("relabeled διαλύομαι->διαλύω; keyed G1262 (headword form)", now, t["id"]))
            relabeled = 1

        # ---- διαλιμπάνω(1182) key G1257 (byform of διαλείπω) ----
        deon = 0
        e = con.execute("SELECT strongs FROM entries WHERE id=1182").fetchone()
        if e and e["strongs"] != "G1257":
            con.execute("UPDATE entries SET strongs='G1257', lemma_translit='dialeípō' WHERE id=1182")
            con.execute("""INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value,
                           resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)""",
                        (1182, "strongs", "NULL (unmatched; -λιμπάνω byform)", "G1257",
                         "διαλιμπάνω is the -λιμπάνω present byform of διαλείπω G1257 (body cites Ac 8²² D*); not separately numbered",
                         "manual:strongs-fix", now))
            deon = 1

    print(f"\napplied (disagreements): {applied}")
    print(f"nt_references added:     {nt_added}")
    print(f"διασπάω fragment move:   {moved}")
    print(f"διαλύω relabel (1187):   {relabeled}")
    print(f"διαλιμπάνω key (1182):   {deon}")
    print(f"skipped already-resolved: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
