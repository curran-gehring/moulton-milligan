"""Phase 5af: residual disagreement sweep for the 561-600 batch (waves BA-BD).

Auto-resolver (phase5_resolve) closed 79 of 105. This handles the remaining 26.

MERGE continuation fragments into the prior-page truncated entry (body smart-join +
UNION nt_references & papyri_citations, then delete fragment + reviews/disagreements).
Target = prior-page max-position entry = id-1 in every case (verified). 26 merges span
the whole Π-tail → Ρ → Σ run; most share the head's lemma so they were NOT flagged as
lemma disagreements (auto-resolver passed them through as continuation notes) — they are
identified structurally: pos=1 entry whose parse-JSON note says "continuation from prior
page". Three carried still-open lemma disagreements (4058 προοιμάζομαι, 4121 προσμένω→
προσλαμβάνω, 4144 προσφωνέω→continuation) which the merge deletes.

ADOPT-REVIEWER (Codex caught a genuine producer error):
  id 4216 πώρωσις → πωρόω  G4457→G4456 : p591 has TWO "πώρωσις" entries; pos4's body
        glosses '"petrify," "tender." ... cf. πώρωσις.' = the VERB πωρόω (the real noun
        πώρωσις is pos5 id4217, kept at G4457).
  id 4249 ῥύομαι → ῥίπτω   G4506→G4496 : ῥύομαι is impossible on p594 (it is p595's first
        headword); the entry between ῥιπτέω and Ῥόδη is ῥίπτω (G4496).
  id 4256 Ῥοῦβος → Ῥοῦφος  : OCR β-for-φ on the Rufus name (Rom 16¹³, Mk 15²¹); fix lemma
        + body (strongs already G4504 via phase3b).
  id 4254 ῥομφαία nt += Rev: body says "found *sexies* in Rev, and once... in Lk 2³⁵" →
        Rev 1¹⁶,2¹²,2¹⁶,6⁸,19¹⁵,19²¹ + Lk 2³⁵ (G4501).
  id 4270 σαβαώθ nt += Rom 9²⁹ : body literally cites "(Rom 9²⁹ LXX, Jas 5⁴)"; Rom 9²⁹ is
        a genuine NT attestation (Paul quoting Isaiah — Romans IS NT).

KEEP-PRODUCER (benign — producer is correct, reviewer misread; or cosmetic):
  Producer-correct lemmas/refs the reviewer garbled: 4022 προαιρέω (OCR headword
  προχειρέω was wrong; body = προαιρέω 2 Cor 9⁷), 4105 προσήλυτος (rev dropped accent),
  4106 πρόσκαιρος (rev dropped accent) + its ref 2 Cor 4¹⁸ (rev typo "4 Cor"), 3991 πού
  (interrogative/enclitic homograph accent). Cosmetic citation/superscript/format diffs:
  πρεσβεύω, πρό, προθεσμία (OCR oί/of), προσαγορεύω, προσάγω, προσαγωγή, προσδέχομαι,
  προσφέρω, πυλών, πῦρ (rev parenthetical), σάκκος.
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


# (frag_id, head_id) — head = prior-page max-position entry (= frag_id - 1)
MERGES = [
    (3984, 3983), (3994, 3993), (4000, 3999), (4005, 4004), (4016, 4015),
    (4030, 4029), (4039, 4038), (4050, 4049), (4058, 4057), (4063, 4062),
    (4069, 4068), (4080, 4079), (4103, 4102), (4121, 4120), (4131, 4130),
    (4138, 4137), (4144, 4143), (4151, 4150), (4157, 4156), (4163, 4162),
    (4175, 4174), (4203, 4202), (4243, 4242), (4258, 4257), (4276, 4275),
    (4301, 4300),
]

# id -> (new_lemma_or_None, new_strongs_or_None, new_translit_or_None, body_sub_or_None)
ADOPT_ENTRY = {
    4216: ("πωρόω", "G4456", "pōróō", None),
    4249: ("ῥίπτω", "G4496", "rhíptō", None),
    4256: ("Ῥοῦφος", None, None, ("Ῥοῦβος", "Ῥοῦφος")),
}

# disagreement_id -> entry_id for adopt-entry resolutions (lemma/body diffs)
ADOPT_ENTRY_DIDS = {1385: 4216, 1399: 4249, 1402: 4256, 1403: 4256}

# disagreement_id -> (entry_id, new_nt_references list)
ADOPT_NT = {
    1401: (4254, ["Rev 1¹⁶", "Rev 2¹²", "Rev 2¹⁶", "Rev 6⁸", "Rev 19¹⁵", "Rev 19²¹", "Lk 2³⁵"]),
    1411: (4270, ["Rom 9²⁹", "Jas 5⁴"]),
}

KEEP = [1316, 1320, 1324, 1325, 1333, 1343, 1344, 1345, 1348, 1350,
        1352, 1353, 1364, 1377, 1378, 1412]


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

        # adopt-reviewer entry-level fixes (lemma/strongs/translit/body)
        for eid, (lemma, strongs, translit, body_sub) in ADOPT_ENTRY.items():
            row = con.execute("SELECT lemma_greek, body_markdown FROM entries WHERE id=?", (eid,)).fetchone()
            if not row:
                continue
            new_lemma = lemma if lemma is not None else row["lemma_greek"]
            new_body = row["body_markdown"]
            if body_sub:
                new_body = new_body.replace(body_sub[0], body_sub[1])
            con.execute(
                "UPDATE entries SET lemma_greek=?, body_markdown=? WHERE id=?",
                (new_lemma, new_body, eid),
            )
            if strongs is not None:
                con.execute("UPDATE entries SET strongs=? WHERE id=?", (strongs, eid))
            if translit is not None:
                con.execute("UPDATE entries SET lemma_translit=? WHERE id=?", (translit, eid))

        for did, eid in ADOPT_ENTRY_DIDS.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("adopt reviewer: producer lemma/body error corrected (πωρόω / ῥίπτω / Ῥοῦφος)",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        for did, (eid, nt) in ADOPT_NT.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                        (json.dumps(nt, ensure_ascii=False), eid))
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("adopt reviewer: real NT attestation in body (ῥομφαία Rev *sexies* / σαβαώθ Rom 9²⁹)",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        for did in KEEP:
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("benign: producer correct (reviewer misread accent/headword/ref) or cosmetic "
                         "citation/superscript/format diff",
                         "manual:keep-producer", now, did))
            kept += 1

    print(f"merged: {merged}  adopted: {adopted}  kept: {kept}")
    rem = con.execute("""SELECT COUNT(*) FROM disagreements d JOIN entries e ON e.id=d.entry_id
                         WHERE e.page_no BETWEEN 561 AND 600 AND d.resolution IS NULL""").fetchone()[0]
    print(f"open disagreements 561-600 remaining: {rem}")
    print(f"open DB-wide: {con.execute('SELECT COUNT(*) FROM disagreements WHERE resolution IS NULL').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
