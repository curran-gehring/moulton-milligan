"""Phase 5ah: residual disagreement sweep for the 641-680 batch (Σ-tail->Τ->Υ).

Auto-resolver (phase5_resolve) closed the bulk; this handles the rest.

31 continuation-fragment merges (pure tails; head = frag_id - 1, verified). The
5 differing-lemma frags are all pure tails where the parser grabbed the next/wrong
headword (σύνστοιχος->συστοιχέω, Σωτήρ->σωτήρ, τειχίζω->τεῖχος, τελώνης->τέλος [the
real τελώνης is a separate entry], τι->τις) — no real new headword buried, unlike
the prior batch's Συμεών/στόμα. The merges also delete the 3 open frag disagreements
(d1693 σύνστοιχος, d1731 τειχίζω, d1736 τελώνης lemma flags).

ADOPT-REVIEWER (partial — real NT attestation in body, but reject the wrong one):
  d1763 τρώγω nt -> ["Mt 24³⁸","Jn 6⁵⁴"]: body cites Jn 6⁵⁴ (τρώγων, genuine τρώγω);
        reviewer also proposed Lk 17²⁷ but that verse is ἐσθίω/ἤσθιον, NOT τρώγω — rejected.

KEEP-PRODUCER (cosmetic citation-hygiene / anaphora — Phase 4's job; or producer correct):
  d1692 συνπεριλαμβάνω, d1697 συντίθημι (hyphen rejoin), d1698 συντόμως, d1704 συνχράομαι
  (ib.->BGU IV anaphora), d1708 Σύρος (comma grouping), d1717 σχολάζω, d1728 ταράσσω
  (producer correctly split Ac 17⁸/17¹³ chain), d1748 τις (UPZ anaphora), d1757 τραχύς
  (Lk 3⁵ is NT; the 'LXX' tag is just a quote note, producer correct).
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
    (4682, 4681), (4689, 4688), (4695, 4694), (4702, 4701), (4714, 4713),
    (4723, 4722), (4728, 4727), (4734, 4733), (4738, 4737), (4746, 4745),
    (4754, 4753), (4763, 4762), (4778, 4777), (4787, 4786), (4795, 4794),
    (4803, 4802), (4807, 4806), (4828, 4827), (4835, 4834), (4842, 4841),
    (4853, 4852), (4862, 4861), (4870, 4869), (4876, 4875), (4884, 4883),
    (4893, 4892), (4912, 4911), (4921, 4920), (4940, 4939), (4949, 4948),
    (4957, 4956),
]

ADOPT_NT = {1763: (4919, ["Mt 24³⁸", "Jn 6⁵⁴"])}

KEEP = [1692, 1697, 1698, 1704, 1708, 1717, 1728, 1748, 1757]


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
            if resolve(did, "adopt reviewer: τρώγω += Jn 6⁵⁴ (body); reject Lk 17²⁷ (= ἐσθίω, not τρώγω)",
                       "manual:adopt-reviewer"):
                adopted += 1

        for did in KEEP:
            if resolve(did, "benign: producer correct / cosmetic citation-hygiene-anaphora (Phase 4)",
                       "manual:keep-producer"):
                kept += 1

    print(f"merged: {merged}  adopted: {adopted}  kept: {kept}")
    rem = con.execute("""SELECT COUNT(*) FROM disagreements d JOIN entries e ON e.id=d.entry_id
                         WHERE e.page_no BETWEEN 641 AND 680 AND d.resolution IS NULL""").fetchone()[0]
    print(f"open 641-680 remaining: {rem}")
    print(f"open DB-wide: {con.execute('SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
