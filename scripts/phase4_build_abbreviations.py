"""Phase 4a: build reference/papyri_abbreviations.json from MM's own front matter.

Spec: "Build reference/papyri_abbreviations.json from MM's own front-matter
(the abbreviation table — extract it first, treat it as ground truth)."

Source: scan pages 21-30 (vision-OCR'd), sections:
  I. GENERAL                  (p21-27)
  II. PAPYRI                  (p27-28)
  III. INSCRIPTIONS AND OSTRACA (p29-30)
The trailing "NOTE ON METHOD OF PUBLICATION" on p30 is excluded.

Entry format: "<Abbrev> = <expansion...>" — one logical entry per paragraph;
OCR continuation lines (no " = ") are joined to the previous entry.
`abbrev_clean` strips markdown italics for matching.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"
OUT = ROOT / "reference" / "papyri_abbreviations.json"

SECTIONS = {
    "I. GENERAL": "general",
    "II. PAPYRI": "papyri",
    "III. INSCRIPTIONS AND OSTRACA": "inscriptions",
}


def main() -> int:
    con = sqlite3.connect(DB)
    section = None
    entries = []  # (abbrev_raw, expansion_parts, section)
    stop = False

    for p in range(21, 31):
        text = con.execute("SELECT ocr_text FROM pages WHERE page_no=?", (p,)).fetchone()[0]
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                continue
            # section headers / page furniture
            hdr = line.lstrip("#").strip().rstrip(".")
            if hdr in SECTIONS:
                section = SECTIONS[hdr]
                continue
            if hdr == "ABBREVIATIONS":
                continue
            if "NOTE ON METHOD OF PUBLICATION" in line:
                stop = True
                continue
            if stop:
                continue
            # roman-numeral page furniture like "xxii" alone
            if re.fullmatch(r"x{0,3}(ix|iv|v?i{0,3})", line.lower()):
                continue
            if section is None:
                continue
            if " = " in line:
                abbrev, expansion = line.split(" = ", 1)
                entries.append([abbrev.strip(), [expansion.strip()], section])
            elif entries:
                # continuation line of the previous entry
                entries[-1][1].append(line)

    out = []
    seen = set()
    for abbrev_raw, parts, sec in entries:
        clean = abbrev_raw.replace("*", "").strip().rstrip(".").strip()
        if not clean or clean in seen:
            # keep duplicates visible rather than silently merging
            if clean in seen:
                clean_key = clean + " (dup)"
            else:
                continue
        seen.add(clean)
        out.append({
            "abbrev": abbrev_raw,
            "abbrev_clean": clean,
            "expansion": " ".join(parts).strip(),
            "section": sec,
        })

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {}
    for e in out:
        counts[e["section"]] = counts.get(e["section"], 0) + 1
    print(f"wrote {OUT}: {len(out)} entries  {counts}")
    # spot-check the workhorse series
    have = {e["abbrev_clean"] for e in out}
    for w in ["P Oxy", "BGU", "P Tebt", "P Lond", "P Fay", "P Ryl", "Syll", "OGIS",
              "Chrest. I", "Preisigke", "P Grenf I", "P Grenf II", "P Hib", "P Amh",
              "P Flor", "P Petr", "P Par", "Kaibel", "Magn", "Priene", "Cagnat", "P Strass"]:
        mark = "OK " if any(h == w or h.startswith(w) for h in have) else "MISSING"
        print(f"  [{mark}] {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
