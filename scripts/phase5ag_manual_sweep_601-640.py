"""Phase 5ag: residual disagreement sweep for the 601-640 batch (σ section).

Auto-resolver (phase5_resolve) closed 86 of 132. This handles the remaining 46.

MERGE continuation fragments into the prior-page truncated entry (body smart-join +
UNION nt_references & papyri_citations, then delete fragment + reviews/disagreements).
Target = prior-page max-position entry = id-1 in every case (verified). 24 of the 29
pos-1 continuation fragments are clean pure-tails and are merged here.

5 pos-1 fragments are NOT merged (they carry real new content, not a pure tail):
  id 4493 στόμα   G4750 — real στόμα entry (opening words truncated at p621 bottom);
                          merging into στολή would corrupt it. KEPT as-is.
  id 4544 Συμεών  G4826 — real Συμεών entry (Ac 15:14); only a 1-line σύμβολος tail
                          belongs to σύμβουλος. KEPT as-is.
  id 4581 συμπεριφέρομαι — standalone non-NT (Sir 25:1 only) -> N/A (not συναπάγω).
  id 4618 σύνζυξ        — standalone non-NT adj discussion -> N/A (not συνέχω).
  (id 4637 σύνκλητος already set N/A in phase3b; senate, non-NT — kept standalone.)

ADOPT-REVIEWER (Codex caught genuine producer ref/lemma errors; lemma relabels already
applied in phase3b — here we close their disagreements + adopt the corrected NT refs):
  d1601/1603/1604/1606 p632 lemma relabels (συναναβαίνω/συναναμίγνυμι/συναναπαύομαι/
        συναντάω) — entries already corrected in phase3b; close as adopt-reviewer.
  d1602 συναναβαίνω nt  -> Mk 15:41, Ac 13:31 (producer had OCR-garbled Mk 15:10)
  d1605 συναναπαύομαι nt-> Rom 15:32 (producer empty)
  d1607 συναντάω nt     -> Lk 9:37, Ac 20:22 (producer had OCR-garbled Lk 9:27)
  d1590 σύμβουλος nt    -> Rom 11:34 (body cites it; the "LXX" tag is just a quote note)
  d1618 συνέρχομαι nt   -> [] (drop bare incomplete "Mk" page-edge fragment)

RELABEL-NOTE (phase3b body-derived relabel; neither producer nor Codex lemma adopted):
  d1505 p603 σθένος->σητόβρωτος G4598 (moth-eaten Jas 5:2; Codex guessed σιαγόνιον off
        the OCR heading, producer had σθένος; body is unambiguously σητόβρωτος).

KEEP-PRODUCER (producer correct / reviewer misread / cosmetic citation-hygiene; OT-add
rejected on d1506 [Job 13:28] and d1509):
  d1504 σής (producer-correct; Codex flagged page-heading position), d1506/1508/1509
  (p603 σιαγόνιον placeholder + reject OT Job), d1521/1528-equiv hyphen rejoins
  (1529,1534), d1522/1523 (Luke chain split kept / Jn 19:31 clean), d1537 (cf.14 anaphor),
  d1558/1574/1575/1577/1578/1595/1597/1613/1615/1617/1623/1624 (citation hygiene:
  anaphoric ib./same-doc-line/bare-date/ibid — Phase 4's job), d1585 (*al.* not a
  citation), d1588/1589/1591 (breathing/accent normalization — producer correct),
  d1626 (συνκερόννυμι OCR; producer normalized to συνκεράννυμι->συγκεράννυμι correctly),
  d1620 (σύνζυξ standalone non-NT, kept N/A not merged).
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


# (frag_id, head_id) — clean pure-tail continuations; head = frag_id - 1 (verified)
MERGES = [
    (4312, 4311), (4327, 4326), (4337, 4336), (4348, 4347), (4388, 4387),
    (4398, 4397), (4407, 4406), (4433, 4432), (4443, 4442), (4448, 4447),
    (4457, 4456), (4465, 4464), (4484, 4483), (4499, 4498), (4516, 4515),
    (4528, 4527), (4556, 4555), (4562, 4561), (4565, 4564), (4572, 4571),
    (4592, 4591), (4599, 4598), (4611, 4610), (4631, 4630),
]

# entries to set N/A (standalone non-NT misflagged as continuations) + protect from re-snap
GNA = [4581, 4618]

# disagreement_id -> (entry_id, new_nt_references list)
ADOPT_NT = {
    1602: (4574, ["Mk 15⁴¹", "Ac 13³¹"]),
    1605: (4576, ["Rom 15³²"]),
    1607: (4577, ["Lk 9³⁷", "Ac 20²²"]),
    1590: (4543, ["Rom 11³⁴"]),
    1618: (4610, []),
}

# lemma-relabel disagreements already applied in phase3b — just close them
ADOPT_LEMMA = [1601, 1603, 1604, 1606]

RELABEL_NOTE = [1505]

KEEP = [1504, 1506, 1508, 1509, 1521, 1522, 1523, 1529, 1534, 1537, 1558,
        1574, 1575, 1577, 1578, 1585, 1588, 1589, 1591, 1595, 1597, 1613,
        1615, 1617, 1623, 1624, 1626, 1620]


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    merged = adopted = kept = gna = 0

    def resolve(did, note, by):
        r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
        if not r or r["resolution"] is not None:
            return False
        con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                       WHERE id=? AND resolution IS NULL""", (note, by, now, did))
        return True

    with con:
        # 1) continuation merges
        for frag_id, head_id in MERGES:
            fr = con.execute("SELECT * FROM entries WHERE id=?", (frag_id,)).fetchone()
            hd = con.execute("SELECT * FROM entries WHERE id=?", (head_id,)).fetchone()
            if not fr or not hd:
                continue
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
            merged += 1

        # 2) N/A standalone non-NT fragments + protective tombstone
        for eid in GNA:
            row = con.execute("SELECT lemma_greek FROM entries WHERE id=?", (eid,)).fetchone()
            if not row:
                continue
            con.execute("UPDATE entries SET strongs=NULL WHERE id=?", (eid,))
            has = con.execute(
                """SELECT 1 FROM disagreements WHERE entry_id=?
                   AND resolution_by='manual:strongs-fix' AND reviewer_value='G_N/A'""",
                (eid,)).fetchone()
            if not has:
                con.execute(
                    """INSERT INTO disagreements
                       (entry_id, field, producer_value, reviewer_value,
                        resolution, resolution_by, resolved_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (eid, "strongs", row["lemma_greek"], "G_N/A",
                     "standalone non-NT word misflagged as continuation; kept N/A",
                     "manual:strongs-fix", now))
            gna += 1

        # 3) adopt-reviewer NT-reference fixes
        for did, (eid, nt) in ADOPT_NT.items():
            con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                        (json.dumps(nt, ensure_ascii=False), eid))
            if resolve(did, "adopt reviewer: corrected NT reference (OCR-garbled/missing in producer)",
                       "manual:adopt-reviewer"):
                adopted += 1

        # 4) close lemma relabels already applied in phase3b
        for did in ADOPT_LEMMA:
            if resolve(did, "adopt reviewer: OCR headword mislabel relabeled by body (phase3b)",
                       "manual:adopt-reviewer"):
                adopted += 1

        # 5) body-derived relabel note
        for did in RELABEL_NOTE:
            if resolve(did, "relabeled to σητόβρωτος per body (moth-eaten, Jas 5:2); phase3b",
                       "manual:lemma-swap"):
                adopted += 1

        # 6) keep-producer
        for did in KEEP:
            if resolve(did, "benign: producer correct (reviewer misread / OT-add rejected) or "
                            "cosmetic citation-hygiene/anaphora (Phase 4)", "manual:keep-producer"):
                kept += 1

    print(f"merged: {merged}  adopted: {adopted}  kept: {kept}  gna: {gna}")
    rem = con.execute("""SELECT COUNT(*) FROM disagreements d JOIN entries e ON e.id=d.entry_id
                         WHERE e.page_no BETWEEN 601 AND 640 AND d.resolution IS NULL""").fetchone()[0]
    print(f"open disagreements 601-640 remaining: {rem}")
    print(f"open DB-wide: {con.execute('SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
