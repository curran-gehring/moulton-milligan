"""Build reference/strongs_lemma_index.json from openscriptures + STEPBible TBESG.

Output structure (per spec §6 Phase 0 step 4):
  {
    "G0026": {"lemma": "ἀγάπη", "translit": "agapē", "variants": ["ἀγάπη","ἀγαπη"]},
    ...
  }

variants intentionally include the bare-form (diacritics stripped) string so the
Phase 3 fuzzy matcher can detect OCR drops; Phase 3 still operates on NFC strings
for the canonical compare.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRONGS_XML = ROOT / "reference" / "strongs" / "greek" / "StrongsGreekDictionaryXML_1.4" / "strongsgreek.xml"
TBESG_TXT = ROOT / "reference" / "stepbible" / "Lexicons" / (
    "TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt"
)
OUT_PATH = ROOT / "reference" / "strongs_lemma_index.json"

GREEK_DIACRITIC_RANGES = [
    (0x0300, 0x036F),  # combining diacriticals
]


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def strip_diacritics(s: str) -> str:
    """Drop combining marks; useful for fuzzy snap variants."""
    decomp = unicodedata.normalize("NFD", s)
    out = []
    for ch in decomp:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in GREEK_DIACRITIC_RANGES):
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def parse_strongs_xml() -> dict[str, dict]:
    """Parse openscriptures Strong's Greek XML.

    Returns: { 'G0001': {'lemma': '...', 'translit': '...', 'variants': set(...)} }
    """
    out: dict[str, dict] = {}
    tree = ET.parse(STRONGS_XML)
    root = tree.getroot()
    for entry in root.iter("entry"):
        sid_raw = entry.attrib.get("strongs", "").strip()
        if not sid_raw:
            continue
        # Pad to 4 digits, prefix G
        try:
            sid = f"G{int(sid_raw):04d}"
        except ValueError:
            continue
        greek = entry.find("greek")
        if greek is None:
            continue
        lemma = nfc(greek.attrib.get("unicode", ""))
        translit = greek.attrib.get("translit", "").strip()
        if not lemma:
            continue
        variants = {lemma, strip_diacritics(lemma)}
        out[sid] = {"lemma": lemma, "translit": translit, "variants": variants}
    return out


def parse_tbesg() -> dict[str, dict]:
    """Parse STEPBible TBESG TSV. Field layout (1-indexed):
       1 = base Strong's (G0001)
       2 = extended-Strong's marker
       3 = extended-Strong's
       4 = lemma (Greek polytonic)
       5 = transliteration
       ...
    Multiple rows per base Strong's collect lemma variants into 'variants'.
    """
    out: dict[str, dict] = defaultdict(lambda: {"lemma": "", "translit": "", "variants": set()})
    with TBESG_TXT.open(encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            if not line or not line[0] == "G":
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 5:
                continue
            base = cols[0].strip()
            if not re.match(r"^G\d+$", base):
                continue
            # Pad to G0001 form
            try:
                sid = f"G{int(base[1:]):04d}"
            except ValueError:
                continue
            lemma_field = cols[3].strip()
            translit_field = cols[4].strip()
            # lemma field can have multiple comma-separated tokens (e.g. "Α, α, ἄλφα")
            for tok in re.split(r"[,\s]+", lemma_field):
                tok = nfc(tok)
                if not tok:
                    continue
                # Skip obvious non-Greek tokens (single Latin letters in the comma list)
                if not any(0x0370 <= ord(c) <= 0x03FF or 0x1F00 <= ord(c) <= 0x1FFF for c in tok):
                    continue
                out[sid]["variants"].add(tok)
                out[sid]["variants"].add(strip_diacritics(tok))
                if not out[sid]["lemma"]:
                    out[sid]["lemma"] = tok
                    out[sid]["translit"] = translit_field
    return out


def merge(a: dict[str, dict], b: dict[str, dict]) -> dict[str, dict]:
    """Merge two indices. Prefer openscriptures lemma as canonical; union variants."""
    out: dict[str, dict] = {}
    keys = sorted(set(a) | set(b))
    for k in keys:
        ea = a.get(k)
        eb = b.get(k)
        if ea and eb:
            variants = set(ea["variants"]) | set(eb["variants"])
            out[k] = {
                "lemma": ea["lemma"] or eb["lemma"],
                "translit": ea["translit"] or eb["translit"],
                "variants": sorted(v for v in variants if v),
            }
        elif ea:
            out[k] = {
                "lemma": ea["lemma"],
                "translit": ea["translit"],
                "variants": sorted(v for v in ea["variants"] if v),
            }
        else:
            out[k] = {
                "lemma": eb["lemma"],
                "translit": eb["translit"],
                "variants": sorted(v for v in eb["variants"] if v),
            }
    return out


def main() -> int:
    if not STRONGS_XML.exists():
        print(f"Missing {STRONGS_XML}", file=sys.stderr)
        return 1
    if not TBESG_TXT.exists():
        print(f"Missing {TBESG_TXT}", file=sys.stderr)
        return 1
    strongs = parse_strongs_xml()
    tbesg = parse_tbesg()
    print(f"openscriptures strongs entries: {len(strongs)}")
    print(f"TBESG entries:                  {len(tbesg)}")
    merged = merge(strongs, tbesg)
    print(f"merged entries:                 {len(merged)}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")

    # Sanity examples
    for sid in ("G0026", "G0001", "G2316", "G5547"):
        if sid in merged:
            e = merged[sid]
            print(f"  {sid}  {e['lemma']:<20s}  {e['translit']:<10s}  variants={len(e['variants'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
