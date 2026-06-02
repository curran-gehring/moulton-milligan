"""Phase 5ab: residual disagreement sweep for the 401-440 batch (waves AK-AN).

Auto-resolver closed 46 of 76. This handles the remaining 30.

MERGE continuation fragments into their prior-page head (body concat + NT-ref /
papyri-citation UNION, then delete fragment + its disagreements/reviews). Each
fragment is the tail of the prior page's truncated entry, mislabeled with the
running-header LEFT lemma:
  2911 p413 'λυτρόω'      -> 2910 p412 λύτρον   (λύτρον tail; real λυτρόω separate)
  2955 p419 'Μᾶρκος'      -> 2954 p418 Μαρία    (Μαρία tail; real Μᾶρκος separate)
  2978 p422 'μεγαλαυχέω'  -> 2977 p421 μάχομαι  (μάχομαι tail)
  2993 p424 'μεθιστάνω'   -> 2992 p423 μέθη     (μέθη tail; real μεθίστημι=2994)
  3018 p427 'μέντοι'      -> 3017 p426 μενοῦνγε (μέντοιγε tail; real μέντοι=3019)
μή mega-particle (spans p437-439): merge p438 (3084) + p439-fragment (3085) into
the p437 head (3083, μή G3361) — union the 33+ NT refs and citations.

ADOPT-REVIEWER NT adds (real attestations the producer left in body, or book-
prefix fixes), set as explicit JSON arrays:
  d#899 λαός += 1 Pet 2⁹ ; d#916 Λυσανίας = [Lk 3¹] ; d#920 μᾶλλον += 1 Thess 4¹
  d#926 μαστός += Lk 11²⁷ / Lk 23²⁹ ; d#927 μάχαιρα += Lk 22³⁸ ; d#935 μεθίστημι = [Ac 13²²]
  d#938 μέλλω += Lk 13⁹ / 2 Pet 1¹² ; d#940 μέν (Ac book-prefix) ; d#941 μενοῦνγε += Lk 11²⁸
  d#957 μεταξύ += Rom 2¹⁵
ADOPT body cleanup: d#972 μηδείς — strip the 'PART V.' running-header artifact.

KEEP-PRODUCER (benign): smooth-breathing-on-capital koronis vs apostrophe, hyphen
line-break artifacts, witness sigla / ff. markers, anaphora, identical-after-norm.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"


def _arr(s):
    try:
        v = json.loads(s) if s else []
        return v if isinstance(v, list) else []
    except Exception:
        return []


def union(*jsons):
    out, seen = [], set()
    for j in jsons:
        for x in _arr(j):
            if x not in seen:
                seen.add(x)
                out.append(x)
    return json.dumps(out, ensure_ascii=False)


def smart_join(head, frag):
    h = (head or "").rstrip()
    f = (frag or "").lstrip()
    return (h[:-1] + f) if h.endswith("-") else (h + " " + f)


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    merged = adopted = kept = 0

    def do_merge(frag_id, head_id):
        fr = con.execute("SELECT * FROM entries WHERE id=?", (frag_id,)).fetchone()
        hd = con.execute("SELECT * FROM entries WHERE id=?", (head_id,)).fetchone()
        if not fr or not hd:
            return False
        con.execute(
            "UPDATE entries SET body_markdown=?, nt_references=?, papyri_citations=? WHERE id=?",
            (smart_join(hd["body_markdown"], fr["body_markdown"]),
             union(hd["nt_references"], fr["nt_references"]),
             union(hd["papyri_citations"], fr["papyri_citations"]),
             head_id),
        )
        con.execute("DELETE FROM disagreements WHERE entry_id=?", (frag_id,))
        con.execute("DELETE FROM reviews WHERE entry_id=?", (frag_id,))
        con.execute("DELETE FROM entries WHERE id=?", (frag_id,))
        return True

    with con:
        # --- continuation merges ---
        for frag, head in [(2911, 2910), (2955, 2954), (2978, 2977),
                           (2993, 2992), (3018, 3017),
                           (3084, 3083), (3085, 3083)]:
            if do_merge(frag, head):
                merged += 1

        # --- adopt-reviewer NT adds (explicit JSON arrays) ---
        nt_adds = {
            899: (2831, ["1 Pet 2⁹"]),
            916: (2906, ["Lk 3¹"]),
            920: (2941, ["Phil 1⁹", "1 Thess 4¹"]),
            926: (2969, ["Rev 1¹³R", "Lk 11²⁷", "Lk 23²⁹ DFG"]),
            927: (2975, ["1 Cor 4²¹", "Lk 22³⁸", "Rom 13⁴"]),
            935: (2994, ["Ac 13²²"]),
            938: (3009, ["Lk 13⁹", "Mt 24⁶", "2 Pet 1¹²"]),
            940: (3015, ["Rom 1⁸", "Ac 1⁶", "Ac 9³¹"]),
            941: (3017, ["Rom 10¹⁸", "Lk 11²⁸"]),
            957: (3060, ["Mt 18¹⁵", "Rom 2¹⁵", "Jn 4³¹"]),
        }
        for did, (eid, nt) in nt_adds.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                        (json.dumps(nt, ensure_ascii=False), eid))
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("adopt reviewer: real NT attestation(s) producer left in body / book-prefix fix",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        # --- d#972 μηδείς: strip 'PART V.' running-header artifact from body ---
        r = con.execute("SELECT resolution FROM disagreements WHERE id=972").fetchone()
        if r and r["resolution"] is None:
            b = con.execute("SELECT body_markdown FROM entries WHERE id=3089").fetchone()["body_markdown"]
            con.execute("UPDATE entries SET body_markdown=? WHERE id=3089",
                        (b.replace("PART V. ", "").replace("PART V.", ""),))
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=972 AND resolution IS NULL""",
                        ("adopt reviewer: strip 'PART V.' running-header artifact from body",
                         "manual:adopt-reviewer", now))
            adopted += 1

        # --- keep-producer (benign residue) ---
        keep = [901, 902, 909, 910, 914, 932, 937, 944, 945, 954, 955, 956, 958, 970]
        for did in keep:
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("benign: koronis/breathing-on-capital vs apostrophe, hyphen line-break, "
                         "witness siglum / ff. marker, citation anaphora, identical-after-normalization",
                         "manual:keep-producer", now, did))
            kept += 1

    print(f"merged: {merged}  adopted: {adopted}  kept: {kept}")
    rem = con.execute("""SELECT COUNT(*) FROM disagreements d JOIN entries e ON e.id=d.entry_id
                         WHERE e.page_no BETWEEN 401 AND 440 AND d.resolution IS NULL""").fetchone()[0]
    print(f"open disagreements 401-440 remaining: {rem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
