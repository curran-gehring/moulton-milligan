"""Book-wide programmatic hunt for placeholder/truncated/suspicious bodies (no vision)."""
import sqlite3, re, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect("out/mm.sqlite"); c.row_factory = sqlite3.Row
rows = list(c.execute("SELECT rowid,strongs,lemma_greek,body_markdown,source_page FROM mm_entries"))

GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
hits = {}
def add(cat, r, extra=""):
    hits.setdefault(cat, []).append(f"p{r['source_page']} {r['lemma_greek']} [{r['strongs']}] {extra}")

PLACEHOLDER = re.compile(r"\(see note\.?\)|\bTODO\b|\bplaceholder\b|\bXXX\b|\bFIXME\b|not transcribed|illegible\]?$", re.I)
for r in rows:
    b = (r["body_markdown"] or "").strip()
    # placeholder/marker text
    if PLACEHOLDER.search(b):
        add("placeholder_marker", r, repr(b[:50]))
    # body that is ONLY a parenthetical or bracket fragment
    if b and b[0] in "([" and len(b) < 25:
        add("tiny_paren_body", r, repr(b))
    # ends with an open bracket / dangling (possible truncation) — but lacunae are legit, so flag only if very short
    if b.endswith(("(", "[", "—", ":")) and len(b) < 40:
        add("dangling_short", r, repr(b[-30:]))
    # body with no Greek at all AND short (real entries cite Greek papyri)
    if len(b) < 80 and not GREEK.search(b):
        add("nogreek_short", r, repr(b[:60]))
    # repeated 'See s.v.' but longer than a stub (could be mis-split) - informational
    # control chars
    if any(ord(ch) < 9 or (13 < ord(ch) < 32) for ch in b):
        add("control_chars", r)

for cat in sorted(hits):
    print(f"\n## {cat} ({len(hits[cat])})")
    for m in hits[cat][:60]:
        print("  ", m)
if not hits:
    print("No anomalies.")
