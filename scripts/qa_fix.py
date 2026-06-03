"""Whole-book QA fixes (driven by scripts/qa_audit.py findings).

 1. Literal 'G_N/A' strongs (7) -> NULL + protective tombstone (honest coverage;
    the literal string both inflated the keyed metric and broke the export's
    G_N/A:<lemma> convention).
 2. Document the 5 deliberate reachability keys with resolved manual:strongs-fix
    rows (κρείττων G2909, παρίστημι G3936, πειθός G3981, συναλλάσσω G4900,
    Φιλαδελφία G5359) so audits stop flagging them.
 3. Tombstone the 31 legit-NULL entries that predate the tombstone convention.
 4. Strip embedded page furniture ("PART VII."/"PART VIII." lines) from bodies.
 5. Merge the early-wave (pages 31-399) unmerged same-lemma page-boundary
    continuation pairs — the export dedup had been CLIPPING the shorter half of
    each pair. Guard: skip pairs whose two sides carry different non-NULL
    Strong's (potential homograph) and report them instead.
 6. id261 ('??' lemma, p53 pos1): alpha-chunk continuation fragment -> merge
    into the last entry of p52.
 7. Bare chain NT refs (alpha-era): a ref with no book prefix inherits the book
    of the nearest preceding prefixed ref in the same array.

Idempotent. Run qa_audit.py again afterwards.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"

NT_BOOKS = (
    "Mt|Matt|Matthew|Mk|Mark|Lk|Luke|Jn|John|Ac|Acts|Rom|1 Cor|2 Cor|Gal|Eph|Phil|Philem|Phlm|"
    "Col|1 Thess|2 Thess|1 Th|2 Th|1 Tim|2 Tim|Tit|Heb|Jas|1 Pet|2 Pet|2 Peter|1 Jn|2 Jn|3 Jn|"
    "1 John|2 John|3 John|Jude|Rev"
)
BOOK_RE = re.compile(rf"^\[?({NT_BOOKS})(?=$|[\s¹²³⁴⁵⁶⁷⁸⁹⁰.:\]])")

EXEMPT_KEYS = [
    (2745, "G2909", "κρείσσων/κρείττων adj 'better' = G2909 (index first-form maps G2908 neuter) — deliberate"),
    (3694, "G3936", "παριστάνω/παρίστημι = G3936 (index maps παριστάνω to extended G8653) — deliberate"),
    (3847, "G3981", "πιθός = πειθός 1 Cor 2:4 classic G3981 (index πιθός->extended G8792) — deliberate"),
    (4573, "G4900", "συναλλάσσω Ac 7:26 verse slot συνελαύνω G4900 — deliberate reachability"),
    (5108, "G5359", "Φιλαδελφία the CITY = G5359 (Φιλαδέλφεια); not φιλαδελφία G5360 — deliberate"),
]


def base(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").split(",")[0])
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-zα-ω]", "", s)


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


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    stats = {}

    def tombstone(eid, lemma, note):
        has = con.execute(
            "SELECT 1 FROM disagreements WHERE entry_id=? AND resolution_by='manual:strongs-fix' "
            "AND reviewer_value='G_N/A'", (eid,)).fetchone()
        if not has:
            con.execute(
                "INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value, "
                "resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)",
                (eid, "strongs", lemma, "G_N/A", note, "manual:strongs-fix", now))

    with con:
        # 1. literal 'G_N/A' -> NULL + tombstone
        rows = con.execute("SELECT id, lemma_greek FROM entries WHERE strongs='G_N/A'").fetchall()
        for r in rows:
            con.execute("UPDATE entries SET strongs=NULL WHERE id=?", (r["id"],))
            tombstone(r["id"], r["lemma_greek"], "QA: literal 'G_N/A' string -> NULL (honest coverage)")
        stats["literal_GNA_nulled"] = len(rows)

        # 2. exemption rows for deliberate keys
        n = 0
        for eid, g, note in EXEMPT_KEYS:
            has = con.execute(
                "SELECT 1 FROM disagreements WHERE entry_id=? AND resolution_by='manual:strongs-fix'",
                (eid,)).fetchone()
            if not has:
                con.execute(
                    "INSERT INTO disagreements (entry_id, field, producer_value, reviewer_value, "
                    "resolution, resolution_by, resolved_at) VALUES (?,?,?,?,?,?,?)",
                    (eid, "strongs", "(QA exemption)", g, note, "manual:strongs-fix", now))
                n += 1
        stats["exemption_rows"] = n

        # 3. tombstone remaining NULLs without one
        rows = con.execute(
            "SELECT e.id, e.lemma_greek FROM entries e WHERE e.strongs IS NULL AND NOT EXISTS "
            "(SELECT 1 FROM disagreements d WHERE d.entry_id=e.id AND "
            "d.resolution_by='manual:strongs-fix' AND d.reviewer_value='G_N/A')").fetchall()
        for r in rows:
            tombstone(r["id"], r["lemma_greek"], "QA: legit non-NT N/A predating tombstone convention")
        stats["tombstones_added"] = len(rows)

        # 4. strip page furniture from bodies
        rows = con.execute(
            "SELECT id, body_markdown FROM entries WHERE body_markdown LIKE '%PART VII%'").fetchall()
        for r in rows:
            nb = re.sub(r"\s*PART V[I]+\.\s*", " ", r["body_markdown"])
            con.execute("UPDATE entries SET body_markdown=? WHERE id=?", (nb, r["id"]))
        stats["furniture_stripped"] = len(rows)

        # 5+6. early-wave continuation merges
        rows = con.execute(
            "SELECT id, page_no, position_on_page, lemma_greek, strongs FROM entries "
            "ORDER BY page_no, position_on_page").fetchall()
        by_page = {}
        for r in rows:
            by_page.setdefault(r["page_no"], []).append(r)
        pages = sorted(by_page)
        pairs, skipped = [], []
        for p1, p2 in zip(pages, pages[1:]):
            if p2 - p1 != 1:
                continue
            head, frag = by_page[p1][-1], by_page[p2][0]
            same = base(head["lemma_greek"]) == base(frag["lemma_greek"]) and len(base(frag["lemma_greek"])) > 2
            is261 = frag["id"] == 261
            if not (same or is261):
                continue
            if (head["strongs"] and frag["strongs"] and head["strongs"] != frag["strongs"]):
                skipped.append(f"p{p1}->{p2} {head['lemma_greek']} {head['strongs']} vs {frag['strongs']}")
                continue
            pairs.append((frag["id"], head["id"]))
        merged = 0
        for fid, hid in pairs:
            fr = con.execute("SELECT * FROM entries WHERE id=?", (fid,)).fetchone()
            hd = con.execute("SELECT * FROM entries WHERE id=?", (hid,)).fetchone()
            if not fr or not hd:
                continue
            con.execute(
                "UPDATE entries SET body_markdown=?, nt_references=?, papyri_citations=?, "
                "papyri_citations_norm=NULL WHERE id=?",
                (smart_join(hd["body_markdown"], fr["body_markdown"]),
                 union(hd["nt_references"], fr["nt_references"]),
                 union(hd["papyri_citations"], fr["papyri_citations"]), hid))
            con.execute("DELETE FROM disagreements WHERE entry_id=?", (fid,))
            con.execute("DELETE FROM reviews WHERE entry_id=?", (fid,))
            con.execute("DELETE FROM entries WHERE id=?", (fid,))
            merged += 1
        stats["continuations_merged"] = merged
        stats["merge_skipped_homograph"] = len(skipped)
        for s in skipped:
            print("  SKIP (different strongs):", s)

        # 7. bare chain refs inherit preceding book
        n_fix = 0
        for r in con.execute("SELECT id, nt_references FROM entries").fetchall():
            refs = _arr(r["nt_references"])
            if not refs:
                continue
            changed = False
            last_book = None
            out = []
            for ref in refs:
                s = str(ref).strip()
                m = BOOK_RE.match(s)
                if m:
                    last_book = m.group(1)
                    out.append(ref)
                elif last_book and re.match(r"^[\d¹²³⁴⁵⁶⁷⁸⁹⁰]", s):
                    out.append(f"{last_book} {s}")
                    changed = True
                else:
                    out.append(ref)
            if changed:
                con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                            (json.dumps(out, ensure_ascii=False), r["id"]))
                n_fix += 1
        stats["bare_refs_prefixed_entries"] = n_fix

    print(json.dumps(stats, indent=1))
    print("NOTE: merged entries had papyri_citations_norm reset -> re-run phase4_normalize.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
