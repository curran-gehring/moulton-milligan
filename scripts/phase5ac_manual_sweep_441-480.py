"""Phase 5ac: residual disagreement sweep for the 441-480 batch (waves AO-AR).

Auto-resolver closed 39 of 94. This handles the remaining 55.

MERGE continuation fragments into their prior-page truncated entry (body smart-join
+ UNION of nt_references & papyri_citations, then delete fragment + its reviews/
disagreements). Each fragment is the tail of the prior page's last entry, which the
parser mislabeled with the running-header LEFT catchword per RULE 7. Verified: the
target is always the max-position entry on (page-1); here that is id-1 in every case.
Special case: 3145 (p446 '## μοιχάομαι' #1) is really a 2nd paragraph of μοιχαλίς
(Jas 4⁴ μοιχαλίδες, "the fem. μοιχαλίς is alone appropriate") — merge SAME-PAGE into
3144 (μοιχαλίς G3428). The real μοιχάομαι verb is 3146 (Mk 10¹¹·¹², kept, G3429).

ADOPT-REVIEWER nt_references (real NT attestations of the lemma the parser
conservatively left in body, or superscript cleanups), set as explicit JSON arrays.

KEEP-PRODUCER (benign): OCR superscript/typo diffs in body, witness sigla / *al.* /
ff. markers, breathing-variant lemma annotations, citation anaphora, missing
parenthetical date — producer value is correct or equivalent after normalization.
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


# (fragment_id, target_id)
MERGES = [
    (3120, 3119), (3126, 3125), (3135, 3134), (3145, 3144), (3155, 3154),
    (3160, 3159), (3169, 3168), (3197, 3196), (3205, 3204), (3221, 3220),
    (3232, 3231), (3243, 3242), (3249, 3248), (3257, 3256), (3268, 3267),
    (3277, 3276), (3286, 3285), (3300, 3299), (3309, 3308), (3317, 3316),
    (3323, 3322), (3330, 3329), (3337, 3336), (3351, 3350), (3360, 3359),
    (3369, 3368), (3385, 3384), (3392, 3391),
]

# did -> (entry_id, [nt refs])
NT_ADOPT = {
    1004: (3222, ["1 Cor 15³¹", "Ac 26²⁵"]),
    1008: (3240, ["Mt 12²⁰", "1 Cor 15⁵⁴", "1 Cor 15⁵⁷"]),
    1022: (3259, ["[Jn] 5⁴", "Mt 4²³"]),
    1023: (3260, ["Lk 13³⁴"]),
    1025: (3261, ["Lk 2²⁴"]),
    1044: (3324, ["Jude ⁶"]),
    1049: (3335, ["Lk 2¹ ᶠᶠ.", "Col 1²⁵"]),
    1050: (3336, ["Lk 12⁴²", "1 Cor 4²"]),
    1062: (3355, ["1 Thess 5³", "2 Thess 1⁹"]),
    1064: (3358, ["1 Thess 5¹⁴"]),
    1070: (3376, ["1 Cor 15³³"]),
}

KEEP = [993, 1001, 1014, 1016, 1045, 1046, 1053, 1054, 1055, 1056, 1058, 1063]


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
                        ("adopt reviewer: real NT attestation(s) producer left in body / superscript cleanup",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        for did in KEEP:
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("benign: OCR superscript/typo, witness siglum / *al.* / ff. marker, "
                         "breathing-variant lemma annotation, citation anaphora, missing parenthetical date",
                         "manual:keep-producer", now, did))
            kept += 1

    print(f"merged: {merged}  adopted: {adopted}  kept: {kept}")
    rem = con.execute("""SELECT COUNT(*) FROM disagreements d JOIN entries e ON e.id=d.entry_id
                         WHERE e.page_no BETWEEN 441 AND 480 AND d.resolution IS NULL""").fetchone()[0]
    print(f"open disagreements 441-480 remaining: {rem}")
    print(f"open DB-wide: {con.execute('SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
