"""Phase 5ad: residual disagreement sweep for the 481-520 batch (waves AS-AV).

Auto-resolver closed 56 of 112. This handles the remaining 56.

MERGE continuation fragments into their prior-page truncated entry (body smart-join
+ UNION of nt_references & papyri_citations, then delete fragment + its reviews/
disagreements). Target = max-position entry on (page-1) = id-1 in every standard
case (verified). NOTE: for frag 3443 the structural target 3442 (ὀρθοτομέω) is
correct and the Codex reviewer_lemma 'ὀρθός' was wrong — the body ('MGr ὀρθὰ κοπτά')
is the ὀρθοτομέω tail. Specials: the παρά preposition mega spans p508(head 3585)→
p509(3586)→p510-tail(3587) — merge BOTH 3586 and 3587 into 3585; the ὀψώνιον mega
spans p501(head 3540)→p502(3541) — merge 3541 into 3540.

ADOPT-REVIEWER nt_references (real NT attestations the parser left in body):
  3406 ὀνίνημι += Philem²⁰ ; 3462 ὁροθεσία = [Ac 17²⁶] ; 3511 οὐσία = [Lk 15¹²ᶠ·]
  3537 ὄψιμος = [Jas 5⁷] ; 3591 παραβάτης += Lk 6⁴ (Cod. Bezae tradition)
ADOPT body fix: 3628 παρακύπτω — restore dropped word 'δια[φ]έρον[τ]ί' in the P Oxy
  will quotation (verified vs page-516 vision: '...πράγμα[τ]ι δια[φ]έρον[τ]ί μοι.').

KEEP-PRODUCER (benign): OCR omicron/typo in English glosses, italic-siglum vs
unitalicized-source convention diffs (we DO italicize papyrus sigla — 8 p507
entries), smooth-breathing-vs-apostrophe, citation anaphora, epigraphic-corpus
refs (C. and B. = Ramsay inscriptions, stay in papyri), garbled reviewer Lk ref
on ὄνος.
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
    (3405, 3404), (3408, 3407), (3413, 3412), (3422, 3421), (3428, 3427),
    (3433, 3432), (3443, 3442), (3453, 3452), (3461, 3460), (3468, 3467),
    (3474, 3473), (3480, 3479), (3485, 3484), (3496, 3495), (3503, 3502),
    (3515, 3514), (3521, 3520), (3529, 3528), (3535, 3534), (3564, 3563),
    (3571, 3570), (3601, 3600), (3606, 3605), (3613, 3612), (3620, 3619),
    (3656, 3655),
    # specials
    (3586, 3585), (3587, 3585), (3541, 3540),
]

NT_ADOPT = {
    1094: (3406, ["Philem²⁰"]),
    1123: (3462, ["Ac 17²⁶"]),
    1141: (3511, ["Lk 15¹²ᶠ·"]),
    1150: (3537, ["Jas 5⁷"]),
    1181: (3591, ["Lk 6⁴"]),
}

KEEP = [1104, 1129, 1130, 1140, 1153, 1193, 1198, 1169, 1170, 1171, 1172,
        1173, 1174, 1175, 1176, 1142, 1199, 1158, 1097]


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
                        ("adopt reviewer: real NT attestation producer left in body",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        # body fix: 3628 παρακύπτω restore dropped word
        r = con.execute("SELECT resolution FROM disagreements WHERE id=1201").fetchone()
        if r and r["resolution"] is None:
            b = con.execute("SELECT body_markdown FROM entries WHERE id=3628").fetchone()["body_markdown"]
            nb = b.replace("πράγμα[τ]ί μοι", "πράγμα[τ]ι δια[φ]έρον[τ]ί μοι")
            con.execute("UPDATE entries SET body_markdown=? WHERE id=3628", (nb,))
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=1201 AND resolution IS NULL""",
                        ("adopt reviewer: restore dropped 'δια[φ]έρον[τ]ί' (verified vs page-516 vision)",
                         "manual:adopt-reviewer", now))
            adopted += 1

        for did in KEEP:
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("benign: OCR typo in gloss, italic-siglum convention (we italicize papyrus sigla), "
                         "breathing/apostrophe, citation anaphora, epigraphic-corpus ref (C.&B.), garbled reviewer ref",
                         "manual:keep-producer", now, did))
            kept += 1

    print(f"merged: {merged}  adopted: {adopted}  kept: {kept}")
    rem = con.execute("""SELECT COUNT(*) FROM disagreements d JOIN entries e ON e.id=d.entry_id
                         WHERE e.page_no BETWEEN 481 AND 520 AND d.resolution IS NULL""").fetchone()[0]
    print(f"open disagreements 481-520 remaining: {rem}")
    print(f"open DB-wide: {con.execute('SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
