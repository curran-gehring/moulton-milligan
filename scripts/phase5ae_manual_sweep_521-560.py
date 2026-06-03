"""Phase 5ae: residual disagreement sweep for the 521-560 batch (waves AW-AZ).

MERGE continuation fragments into prior-page truncated entry (body smart-join +
UNION nt_references & papyri_citations, then delete fragment + reviews/disagreements).
Target = prior-page max-position entry = id-1 in every case.

This Π stretch is mega-entry-heavy: MANY continuations share the head's lemma
(παρίστημι, περί, ποιέω, πόλις, πιπράσκω, πορεύομαι, παροικία, περιβάλλω, ...) so they
are NOT flagged as lemma_greek disagreements. Identified them by: pos=1 AND
base(lemma)==base(prior-page last lemma). Excluded 5 FALSE POSITIVES where a real
new headword merely shares a 5-char prefix with the prior word (parser confirmed
NO continuation; each has its own NT ref): πατρικός(3726,Gal1¹⁴), περιποίησις(3807),
περιτρέχω(3822,Mk6⁵⁵), πλεονέκτης(3888), πορφυρόπωλις(3975,Ac16¹⁴). Added 2 the
heuristic missed (continuation lemma differs from both catchword and head):
πήλινος(3841→πηλός), πλατεῖα(3882→πλατύς; 547 left-catchword is πλεῖστος, so πλατεῖα
is the πλατύς continuation body, not a live headword — folds into πλατύς).

ADOPT-REVIEWER nt_references (real NT attestations producer left in body / book-prefix
/ superscript cleanup; NOTE several parsers wrongly excluded Acts & Luke as "out of
scope" — Acts/Luke ARE NT):
  3674 πάρειμι += Heb 12¹¹ ; 3685 παρεπίδημος book-prefix fix (2¹¹->1 Pet 2¹¹)
  3761 πένθος = Jas 4⁹ ; 3762 πενιχρός = Lk 21² ; 3769 περαιτέρω = Ac 19³⁹
  3787 περιέχω += Lk 5⁹ ; 3883 πλεῖστος = 1 Cor 14²⁷ ; 3886 πλεονάζω = 1 Thess 3¹²
  3887 πλεονεκτέω = 1 Thess 4⁶/2 Cor 2¹¹ ; 3932 ποιμαίνω superscript cleanup
  3961 Πόπλιος = Ac 28⁷ (parser wrongly dropped as non-NT)

KEEP-PRODUCER (benign): OCR breathing/accent/diphthong in Greek body, witness sigla /
*al.* / ff. markers, citation anaphora/formatting, dubious reviewer adds rejected
(πλέω↛Gal 4¹³, πληθύνω↛Col 2¹⁹ — verb does not occur there; πλείων 'Ac (quater)' too
vague to make explicit).
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


MERGES = [
    (3663, 3662), (3673, 3672), (3683, 3682), (3689, 3688), (3695, 3694),
    (3700, 3699), (3712, 3711), (3719, 3718), (3743, 3742), (3760, 3759),
    (3774, 3773), (3780, 3779), (3788, 3787), (3814, 3813), (3841, 3840),
    (3860, 3859), (3865, 3864), (3870, 3869), (3882, 3881), (3901, 3900),
    (3917, 3916), (3927, 3926), (3940, 3939), (3944, 3943), (3964, 3963),
]

NT_ADOPT = {
    1223: (3674, ["Lk 13¹", "Mt 26⁵⁰ *al.*", "Heb 12¹¹"]),
    1227: (3685, ["1 Pet 1¹", "1 Pet 2¹¹", "Heb 11¹³"]),
    1259: (3761, ["Jas 4⁹ *al.*"]),
    1260: (3762, ["Lk 21²"]),
    1261: (3769, ["Ac 19³⁹"]),
    1264: (3787, ["1 Pet 2⁶", "Lk 5⁹"]),
    1281: (3883, ["1 Cor 14²⁷"]),
    1283: (3886, ["1 Thess 3¹²"]),
    1284: (3887, ["1 Thess 4⁶", "2 Cor 2¹¹"]),
    1292: (3932, ["Jn 21¹⁵", "Jn 21¹⁷", "Jn 21¹⁶", "Rev 2²⁷"]),
    1296: (3961, ["Ac 28⁷ ᶠ·"]),
}

KEEP = [1228, 1229, 1243, 1244, 1267, 1268, 1282, 1285, 1286, 1298, 1300,
        1301, 1233, 1236, 1239, 1250, 1254, 1255, 1256, 1273]


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
        for frag, head in MERGES:
            if do_merge(frag, head):
                merged += 1

        for did, (eid, nt) in NT_ADOPT.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                        (json.dumps(nt, ensure_ascii=False), eid))
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("adopt reviewer: real NT attestation producer left in body / book-prefix / cleanup",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        for did in KEEP:
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("benign: OCR breathing/accent/diphthong, witness siglum / *al.* / ff. marker, "
                         "citation anaphora/formatting; dubious reviewer adds rejected (πλέω/πληθύνω verse, πλείων vague)",
                         "manual:keep-producer", now, did))
            kept += 1

    print(f"merged: {merged}  adopted: {adopted}  kept: {kept}")
    rem = con.execute("""SELECT COUNT(*) FROM disagreements d JOIN entries e ON e.id=d.entry_id
                         WHERE e.page_no BETWEEN 521 AND 560 AND d.resolution IS NULL""").fetchone()[0]
    print(f"open disagreements 521-560 remaining: {rem}")
    print(f"open DB-wide: {con.execute('SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
