"""Independent microscopic audit of out/mm.sqlite. Read-only."""
import sqlite3, json, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")

DB = "out/mm.sqlite"
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
rows = list(c.execute("SELECT rowid,* FROM mm_entries"))
print(f"total rows: {len(rows)}")

def gchars(s):
    return [ch for ch in s if "Ͱ" <= ch <= "Ͽ" or "ἀ" <= ch <= "῿"]

issues = {}
def add(cat, msg):
    issues.setdefault(cat, []).append(msg)

GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
STRONGS = re.compile(r"^G\d+$")
NA_STRONGS = re.compile(r"^G_N/A:")

for r in rows:
    rid = r["rowid"]
    s = r["strongs"]
    lem = r["lemma_greek"]
    body = r["body_markdown"]
    pg = r["source_page"]

    # strongs format
    if s is None:
        add("strongs_null", rid)
    elif not STRONGS.match(s):
        if NA_STRONGS.match(s):
            add("strongs_na_placeholder", f"{rid} {s}")
        else:
            add("strongs_bad_format", f"{rid} {s!r} {lem}")

    # lemma must contain greek
    if not lem or not GREEK.search(lem):
        add("lemma_no_greek", f"{rid} {s} {lem!r}")

    # body present
    if not body or not body.strip():
        add("body_empty", f"{rid} {s} {lem}")
    elif len(body.strip()) < 12:
        add("body_very_short", f"{rid} {s} {lem}: {body!r}")

    # source page range
    if pg is None or pg < 31 or pg > 735:
        add("page_out_of_range", f"{rid} {s} {lem} pg={pg}")

    # JSON fields valid
    for col in ("papyri_citations", "papyri_citations_norm", "nt_references"):
        v = r[col]
        if v is None or v == "":
            continue
        try:
            j = json.loads(v)
            if not isinstance(j, list):
                add(f"{col}_not_list", f"{rid} {s} {type(j).__name__}")
        except Exception as e:
            add(f"{col}_bad_json", f"{rid} {s}: {e}")

    # control chars / replacement chars in body or lemma
    if "�" in body or "�" in lem:
        add("replacement_char", f"{rid} {s} {lem}")
    # lemma with surrounding markdown junk
    if lem != lem.strip():
        add("lemma_whitespace", f"{rid} {s} {lem!r}")
    if any(ch in lem for ch in "*_[]()"):
        add("lemma_markdown", f"{rid} {s} {lem!r}")

# duplicate strongs (excluding placeholders) - real Strong's should usually be unique-ish but MM may split
from collections import Counter
real = [r["strongs"] for r in rows if r["strongs"] and STRONGS.match(r["strongs"])]
dup = {k:v for k,v in Counter(real).items() if v > 1}
for k,v in sorted(dup.items(), key=lambda x:-x[1]):
    add("strongs_duplicate", f"{k} x{v}")

# duplicate lemma
lemc = Counter(r["lemma_greek"] for r in rows)
for k,v in sorted({k:v for k,v in lemc.items() if v>1}.items(), key=lambda x:-x[1]):
    add("lemma_duplicate", f"{k!r} x{v}")

print("\n=== ISSUE SUMMARY ===")
for cat in sorted(issues):
    print(f"{cat}: {len(issues[cat])}")

print("\n=== DETAILS (capped) ===")
for cat in sorted(issues):
    print(f"\n## {cat} ({len(issues[cat])})")
    for m in issues[cat][:25]:
        print("  ", m)
