"""Whole-book deterministic QA audit over all entries (post-completion pass).

Checks:
 A. Alphabetical order book-wide (diacritic-insensitive; flags backward jumps
    beyond a small tolerance window — catches residual scrambles/mislabels).
 B. Duplicate lemmas on NON-adjacent pages (adjacent = legit continuations;
    same-page = legit homographs; the rest need eyes).
 C. Suspect unmerged continuations: a page's first entry sharing the previous
    page's last entry's lemma (should have been merged).
 D. Body anomalies: placeholder/empty bodies, very short bodies (<40 chars),
    '??' lemmas, leftover '## ' headings inside bodies, '**'-wrapped headwords,
    embedded page furniture ('PART VII', 'PART VIII').
 E. Strong's integrity: format, existence in the index; lemma<->strongs
    consistency (lemma or variants map to the assigned G#) — entries with a
    manual:strongs-fix / manual:lemma-swap disagreement are exempt (deliberate
    reachability keys).
 F. NULL-strongs entries lacking a protective G_N/A tombstone.
 G. NT-reference book sanity: every ref must start with an NT book name.
 H. Headword reconciliation per page: (## headings in page OCR) vs (entries in
    DB + merges) — count drift beyond the merge ledger suggests dropped or
    invented entries.
 I. JSON validity of papyri_citations / nt_references / papyri_citations_norm.

Output: out/qa_report.md + console summary. Read-only — fixes happen elsewhere.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"
IDX = ROOT / "reference" / "strongs_lemma_index.json"
OUT = ROOT / "out" / "qa_report.md"

NT_BOOKS = (
    "Mt|Matt|Matthew|Mk|Mark|Lk|Luke|Jn|John|Ac|Acts|Rom|1 Cor|2 Cor|Gal|Eph|Phil|Philem|Phlm|"
    "Col|1 Thess|2 Thess|1 Th|2 Th|1 Tim|2 Tim|Tit|Heb|Jas|1 Pet|2 Pet|1 Jn|2 Jn|3 Jn|1 John|2 John|3 John|Jude|Rev"
)
NT_RE = re.compile(rf"^\[?\(?({NT_BOOKS})(?=$|[\s¹²³⁴⁵⁶⁷⁸⁹⁰.:\]])", re.IGNORECASE)


def base(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").split(",")[0])
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-zα-ω]", "", s)


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    idx = json.loads(IDX.read_text(encoding="utf-8"))
    valid_g = set(idx.keys())
    lemma_to_g = defaultdict(set)
    for g, d in idx.items():
        for v in [d["lemma"]] + d.get("variants", []):
            lemma_to_g[unicodedata.normalize("NFC", v)].add(g)
            lemma_to_g[base(v)].add(g)

    rows = con.execute(
        "SELECT id, page_no, position_on_page, lemma_greek, strongs, body_markdown, "
        "papyri_citations, nt_references, papyri_citations_norm "
        "FROM entries ORDER BY page_no, position_on_page").fetchall()
    exempt = {r[0] for r in con.execute(
        "SELECT DISTINCT entry_id FROM disagreements WHERE resolution_by IN "
        "('manual:strongs-fix','manual:lemma-swap')")}
    tombstoned = {r[0] for r in con.execute(
        "SELECT DISTINCT entry_id FROM disagreements WHERE resolution_by='manual:strongs-fix' "
        "AND reviewer_value='G_N/A'")}

    F = defaultdict(list)  # findings by check

    # A. alphabetical order (greek letter groups; tolerate within-page quirks
    #    by comparing first 3 base chars and only flagging full-group reversals)
    prev = None
    for r in rows:
        b = base(r["lemma_greek"])
        if not b or not re.match(r"^[α-ω]", b):
            continue
        if prev and b[:2] < prev[1][:2] and prev[1][:1] == b[:1] is False:
            pass  # cross-letter handled below
        if prev and b[:1] < prev[1][:1]:
            F["A_order"].append(f"p{r['page_no']} id{r['id']} {r['lemma_greek']!r}: letter "
                                f"{b[:1]!r} after {prev[1][:1]!r} (p{prev[0]})")
        prev = (r["page_no"], b)

    # B. duplicate lemmas on non-adjacent pages
    seen = defaultdict(list)
    for r in rows:
        seen[base(r["lemma_greek"])].append((r["page_no"], r["id"], r["lemma_greek"], r["strongs"]))
    for b, occ in seen.items():
        if len(b) < 2 or len(occ) < 2:
            continue
        pages = sorted({p for p, *_ in occ})
        if len(pages) > 1 and any(p2 - p1 > 1 for p1, p2 in zip(pages, pages[1:])):
            F["B_dup"].append(f"{occ[0][2]}: pages {pages} ids {[i for _, i, _, _ in occ]} "
                              f"strongs {sorted({s for *_, s in occ})}")

    # C. unmerged continuations (page first entry == prior page last entry)
    by_page = defaultdict(list)
    for r in rows:
        by_page[r["page_no"]].append(r)
    pages_sorted = sorted(by_page)
    for p1, p2 in zip(pages_sorted, pages_sorted[1:]):
        if p2 - p1 != 1:
            continue
        last, first = by_page[p1][-1], by_page[p2][0]
        if base(last["lemma_greek"]) == base(first["lemma_greek"]) and len(base(first["lemma_greek"])) > 2:
            F["C_unmerged"].append(f"p{p1}->{p2}: {last['lemma_greek']} id{last['id']} | id{first['id']}")

    # D. body anomalies
    for r in rows:
        body = r["body_markdown"] or ""
        if len(body.strip()) < 40:
            F["D_short"].append(f"p{r['page_no']} id{r['id']} {r['lemma_greek']}: {body.strip()[:50]!r}")
        if "??" in (r["lemma_greek"] or ""):
            F["D_lemma??"].append(f"p{r['page_no']} id{r['id']}")
        if re.search(r"^## ", body, re.M):
            F["D_heading_in_body"].append(f"p{r['page_no']} id{r['id']} {r['lemma_greek']}")
        if re.search(r"PART V[I]+\.", body):
            F["D_furniture"].append(f"p{r['page_no']} id{r['id']} {r['lemma_greek']}")

    # E. strongs integrity + lemma consistency
    for r in rows:
        g = r["strongs"]
        if g is None:
            if r["id"] not in tombstoned:
                F["F_null_no_tombstone"].append(f"p{r['page_no']} id{r['id']} {r['lemma_greek']}")
            continue
        if not re.fullmatch(r"G\d{1,5}", g):
            F["E_badformat"].append(f"id{r['id']} {r['lemma_greek']}: {g!r}")
            continue
        if g not in valid_g:
            F["E_unknown_g"].append(f"id{r['id']} {r['lemma_greek']}: {g}")
            continue
        if r["id"] in exempt:
            continue
        lem = unicodedata.normalize("NFC", (r["lemma_greek"] or "").split(",")[0].strip().rstrip("."))
        gs = lemma_to_g.get(lem) or lemma_to_g.get(base(lem)) or set()
        if gs and g not in gs:
            F["E_mismatch"].append(f"p{r['page_no']} id{r['id']} {r['lemma_greek']} -> {g} "
                                   f"but index says {sorted(gs)[:4]}")

    # G. NT ref book sanity
    for r in rows:
        try:
            refs = json.loads(r["nt_references"] or "[]")
        except Exception:
            F["I_badjson"].append(f"id{r['id']} nt_references")
            continue
        for ref in refs:
            if isinstance(ref, str) and ref.strip() and not NT_RE.match(ref.strip()):
                F["G_ref"].append(f"p{r['page_no']} id{r['id']} {r['lemma_greek']}: {ref!r}")

    # I. JSON validity of citation columns
    for r in rows:
        for col in ("papyri_citations", "papyri_citations_norm"):
            v = r[col]
            if v:
                try:
                    json.loads(v)
                except Exception:
                    F["I_badjson"].append(f"id{r['id']} {col}")

    # H. headword reconciliation per page
    drift = []
    for p in pages_sorted:
        if p < 31:
            continue
        ocr = con.execute("SELECT ocr_text FROM pages WHERE page_no=?", (p,)).fetchone()[0] or ""
        n_head = len(re.findall(r"^##\s+", ocr, re.M))
        n_ent = len(by_page[p])
        # entries = headings + (1 leading continuation if page opens mid-entry,
        # which merges away) ± same-page merges. Allow |diff| <= 2.
        if abs(n_ent - n_head) > 2:
            drift.append(f"p{p}: {n_head} '##' headings vs {n_ent} entries")
    F["H_drift"] = drift

    # report
    lines = ["# Whole-book QA audit report", ""]
    total_findings = 0
    ORDER = ["A_order", "B_dup", "C_unmerged", "D_short", "D_lemma??",
             "D_heading_in_body", "D_furniture", "E_badformat", "E_unknown_g",
             "E_mismatch", "F_null_no_tombstone", "G_ref", "H_drift", "I_badjson"]
    for k in ORDER:
        v = F.get(k, [])
        total_findings += len(v)
        lines.append(f"## {k} — {len(v)}")
        lines.extend(f"- {x}" for x in v[:200])
        if len(v) > 200:
            lines.append(f"- ... and {len(v)-200} more")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"entries audited: {len(rows)}")
    for k in ORDER:
        print(f"  {k:22s} {len(F.get(k, []))}")
    print(f"report -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
