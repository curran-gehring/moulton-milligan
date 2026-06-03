"""Phase 5ai: residual disagreement sweep for the 681-720 batch (Υ-tail -> Φ -> Χ).

30 continuation-fragment merges (pure tails; head = frag_id - 1 verified). The 6
differing-lemma frags are all pure tails: ὑπηρεσία->ὑπηρετέω, "φέρω"->φελόνης (the
Maunde-Thompson palaeography paragraph is the 2 Tim 4:13 cloak/parchment tail, NOT
a φέρω continuation — OCR agent mislabeled), φιλονικία->φιλον(ε)ικία, "φυσικός"->
φύραμα (the Syll-807 ἀναφυράω tail), χειρίζω->χείρ (cognate tail; bad-snap key was
already reverted in phase3b), χειροτονία->χειροτονέω. The real φέρω/φυσικός/
ὑπηρέτης entries follow separately on their pages. Merges also delete open frag
disagreements d1807/d1821/d1853/d1865.

ADOPT-REVIEWER:
  d1815 ὑποτύπωσις nt -> ["1 Tim 1¹⁶","2 Tim 1¹³","1 Pet 2²¹"] (producer had a
        trailing truncated duplicate "2 Tim").

KEEP-PRODUCER (citation hygiene: ib./follow-on/same-doc-line anaphora = Phase 4's
job; d1843 reviewer wanted a duplicate "Mt 22³⁴ al." — rejected):
  d1790, d1802, d1804, d1827, d1836, d1837, d1843, d1849, d1850, d1852, d1864,
  d1868, d1870.
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
                seen.add(x); out.append(x)
    return json.dumps(out, ensure_ascii=False)


def smart_join(head, frag):
    h = (head or "").rstrip(); f = (frag or "").lstrip()
    return (h[:-1] + f) if h.endswith("-") else (h + " " + f)


MERGES = [
    (4965, 4964), (4969, 4968), (4978, 4977), (4992, 4991), (4999, 4998),
    (5003, 5002), (5009, 5008), (5027, 5026), (5035, 5034), (5043, 5042),
    (5053, 5052), (5081, 5080), (5088, 5087), (5097, 5096), (5104, 5103),
    (5113, 5112), (5119, 5118), (5131, 5130), (5139, 5138), (5155, 5154),
    (5164, 5163), (5195, 5194), (5204, 5203), (5211, 5210), (5228, 5227),
    (5233, 5232), (5242, 5241), (5248, 5247), (5258, 5257), (5270, 5269),
]

ADOPT_NT = {1815: (5045, ["1 Tim 1¹⁶", "2 Tim 1¹³", "1 Pet 2²¹"])}

KEEP = [1790, 1802, 1804, 1827, 1836, 1837, 1843, 1849, 1850, 1852, 1864, 1868, 1870]


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    merged = adopted = kept = 0

    def resolve(did, note, by):
        r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
        if not r or r["resolution"] is not None:
            return False
        con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                       WHERE id=? AND resolution IS NULL""", (note, by, now, did))
        return True

    with con:
        for frag_id, head_id in MERGES:
            fr = con.execute("SELECT * FROM entries WHERE id=?", (frag_id,)).fetchone()
            hd = con.execute("SELECT * FROM entries WHERE id=?", (head_id,)).fetchone()
            if not fr or not hd:
                continue
            con.execute(
                "UPDATE entries SET body_markdown=?, nt_references=?, papyri_citations=? WHERE id=?",
                (smart_join(hd["body_markdown"], fr["body_markdown"]),
                 union(hd["nt_references"], fr["nt_references"]),
                 union(hd["papyri_citations"], fr["papyri_citations"]), head_id))
            con.execute("DELETE FROM disagreements WHERE entry_id=?", (frag_id,))
            con.execute("DELETE FROM reviews WHERE entry_id=?", (frag_id,))
            con.execute("DELETE FROM entries WHERE id=?", (frag_id,))
            merged += 1

        for did, (eid, nt) in ADOPT_NT.items():
            con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                        (json.dumps(nt, ensure_ascii=False), eid))
            if resolve(did, "adopt reviewer: drop truncated duplicate '2 Tim' from ὑποτύπωσις refs",
                       "manual:adopt-reviewer"):
                adopted += 1

        for did in KEEP:
            if resolve(did, "benign: citation-hygiene/anaphora (Phase 4) or duplicate-ref add rejected",
                       "manual:keep-producer"):
                kept += 1

    print(f"merged: {merged}  adopted: {adopted}  kept: {kept}")
    print(f"open DB-wide: {con.execute('SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
