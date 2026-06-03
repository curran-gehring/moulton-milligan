"""Phase 4b: citation normalization against MM's own abbreviation table.

Spec: "For each entry's papyri_citations_raw, normalize each citation against
this table. Citations that fail to match the table go to manual review.
Codex audits a 5% random sample of normalizations as a check."

What this does, per citation (in entry order):
 1. Clean markdown italics/whitespace.
 2. Anaphora expansion: a citation opening with ib./ibid./id. inherits the
    series (+ roman-numeral volume, when the anaphor lacks its own) from the
    nearest preceding matched citation in the same entry.
 3. Longest-prefix match of the cleaned citation against abbrev_clean values
    from reference/papyri_abbreviations.json (word-boundary constrained).
 4. Writes entries.papyri_citations_norm (JSON array, same length/order as the
    raw array) of objects: {raw, norm, series, status} where status is one of
    matched | expanded | unmatched. Raw column is never modified.
 5. Emits out/phase4_unmatched.tsv — distinct unmatched prefixes with counts
    (the manual-review queue).

Run with --dry-run to see match rates without writing.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"
ABBREV = ROOT / "reference" / "papyri_abbreviations.json"
UNMATCHED_OUT = ROOT / "out" / "phase4_unmatched.tsv"

ANAPHOR_RE = re.compile(r"^(ib(?:id)?\.|id\.)\s*", re.IGNORECASE)
VOLUME_RE = re.compile(r"^((?:[IVXL]+|[1-9][0-9]?)\.)\s")


def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace("*", "")
    s = re.sub(r"\s+", " ", s).strip()
    # style/OCR variant: "P. Oxy" -> "P Oxy" (the table prints "P Oxy")
    s = re.sub(r"^P\.\s+", "P ", s)
    return s


def load_series():
    """Alias pool over the WHOLE table (it is all ground truth per spec).

    Aliases per entry: the cleaned headword, plus splits of combined headwords
    ("Syll. and Syll³" -> "Syll", "Syll³"), each with and without a trailing
    period, and with edition superscripts stripped as an extra alias.
    """
    table = json.loads(ABBREV.read_text(encoding="utf-8"))
    pool = set()
    for e in table:
        a = e["abbrev_clean"]
        parts = re.split(r"\s+(?:and|or)\s+", a)
        for p in parts:
            p = p.strip().rstrip(".")
            if not p:
                continue
            pool.add(p)
            # edition-superscript-stripped alias (Syll³ -> Syll)
            stripped = re.sub(r"[¹²³⁴⁵]+$", "", p).rstrip(".")
            if stripped:
                pool.add(stripped)
    # longest first so "P Grenf II" beats "P Grenf I" beats nothing
    return sorted(pool, key=len, reverse=True)


def match_series(c: str, pool) -> str | None:
    for a in pool:
        if c.startswith(a):
            rest = c[len(a):]
            if rest == "" or not rest[:1].isalnum():
                return a
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pool = load_series()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    cols = [r[1] for r in con.execute("PRAGMA table_info(entries)")]
    if "papyri_citations_norm" not in cols and not args.dry_run:
        con.execute("ALTER TABLE entries ADD COLUMN papyri_citations_norm TEXT")

    n_cit = n_match = n_expand = n_unmatch = 0
    unmatched = Counter()
    rows = con.execute(
        "SELECT id, papyri_citations FROM entries ORDER BY page_no, position_on_page"
    ).fetchall()

    for row in rows:
        try:
            cits = json.loads(row["papyri_citations"]) if row["papyri_citations"] else []
        except Exception:
            cits = []
        if not isinstance(cits, list):
            cits = []
        norm_arr = []
        last_series = None
        last_volume = None
        last_document = None

        SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹ⁱᵛˣ"

        def doc_of(rest: str) -> str | None:
            # document number = leading arabic digits of the token after the
            # (optional) volume ("237" in "237¹⁰·²²", "121" in "121⁸⁷")
            dm = re.match(r"(\d+)", rest)
            return dm.group(1) if dm else None

        for raw in cits:
            c = clean(str(raw))
            n_cit += 1
            m = ANAPHOR_RE.match(c)
            if m and last_series:
                tail = c[m.end():]
                vol_m = VOLUME_RE.match(tail)
                line_only = bool(tail) and tail[0] in SUP
                if vol_m:                       # ib. carries its own volume
                    norm = f"{last_series} {tail}".strip()
                    last_volume = vol_m.group(1)
                    last_document = doc_of(tail[vol_m.end():].strip())
                elif line_only and last_document:
                    # ib. with only a line superscript: inherit series+vol+document
                    parts = [last_series]
                    if last_volume:
                        parts.append(last_volume)
                    parts.append(last_document)
                    norm = (" ".join(parts) + tail).strip()
                else:
                    norm = " ".join(x for x in (last_series, last_volume, tail) if x).strip()
                    nd = doc_of(tail)
                    if nd:
                        last_document = nd
                norm_arr.append({"raw": raw, "norm": norm, "series": last_series,
                                 "status": "expanded"})
                n_expand += 1
                continue
            series = match_series(c, pool)
            if series:
                rest = c[len(series):].strip()
                vol_m = VOLUME_RE.match(rest)
                last_series = series
                last_volume = vol_m.group(1) if vol_m else None
                last_document = doc_of(rest[vol_m.end():].strip() if vol_m else rest)
                norm_arr.append({"raw": raw, "norm": c, "series": series,
                                 "status": "matched"})
                n_match += 1
            elif last_series and re.match(r"^\d", c):
                # MM chain style: a bare further-document number in the same
                # series ("Syll 199⁷, 198¹³ ..."). Inherit series (+volume).
                norm = " ".join(x for x in (last_series, last_volume, c) if x).strip()
                last_document = doc_of(c)
                norm_arr.append({"raw": raw, "norm": norm, "series": last_series,
                                 "status": "expanded"})
                n_expand += 1
            elif last_series and last_document and c[:1] in SUP:
                # bare line-superscript of the previous document
                parts = [last_series] + ([last_volume] if last_volume else []) + [last_document]
                norm_arr.append({"raw": raw, "norm": (" ".join(parts) + c).strip(),
                                 "series": last_series, "status": "expanded"})
                n_expand += 1
            else:
                norm_arr.append({"raw": raw, "norm": c, "series": None,
                                 "status": "unmatched"})
                unmatched[c.split("(")[0].strip()[:40]] += 1
                n_unmatch += 1
        if not args.dry_run:
            con.execute("UPDATE entries SET papyri_citations_norm=? WHERE id=?",
                        (json.dumps(norm_arr, ensure_ascii=False), row["id"]))

    if not args.dry_run:
        con.commit()
        with open(UNMATCHED_OUT, "w", encoding="utf-8") as f:
            f.write("count\tcitation_prefix\n")
            for c, n in unmatched.most_common():
                f.write(f"{n}\t{c}\n")

    tot = max(n_cit, 1)
    print(f"citations: {n_cit}")
    print(f"  matched : {n_match} ({100*n_match/tot:.1f}%)")
    print(f"  expanded: {n_expand} ({100*n_expand/tot:.1f}%)  (ib./id. anaphora)")
    print(f"  unmatched: {n_unmatch} ({100*n_unmatch/tot:.1f}%)")
    print(f"distinct unmatched prefixes: {len(unmatched)}")
    for c, n in unmatched.most_common(25):
        print(f"   {n:4d}  {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
