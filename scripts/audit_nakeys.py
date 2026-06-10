"""Check which G_N/A entries are actually keyable against the Strong's index."""
import json, sqlite3, sys, unicodedata, re
sys.stdout.reconfigure(encoding="utf-8")

idx = json.load(open("reference/strongs_lemma_index.json", encoding="utf-8"))

def strip_accents(s):
    n = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in n if unicodedata.category(ch) != "Mn")

def norm(s):
    s = strip_accents(s).lower()
    s = s.replace("ς", "σ")
    s = re.sub(r"[^α-ω]", "", s)
    return s

# reverse map: normalized lemma -> set of strongs (G#### -> G# int form)
rev = {}
for sid, obj in idx.items():
    forms = [obj.get("lemma", "")] + obj.get("variants", [])
    for f in forms:
        if not f:
            continue
        k = norm(f)
        if k:
            rev.setdefault(k, set()).add(sid)

def variants_of_lemma(lem):
    """MM headword may be 'ἁγιότης, ἁγιωσύνη' or 'ἀκριβής, -ῶς' or 'ἀντίλη(μ)ψις'."""
    out = set()
    # remove parenthetical optional letters -> two forms: with and without
    base_with = re.sub(r"\(([^)]*)\)", r"\1", lem)
    base_without = re.sub(r"\([^)]*\)", "", lem)
    for piece in re.split(r"[,;]", base_with) + re.split(r"[,;]", base_without):
        piece = piece.strip()
        if not piece or piece.startswith("-"):
            continue
        out.add(piece)
    return out

c = sqlite3.connect("out/mm.sqlite")
c.row_factory = sqlite3.Row
na = list(c.execute("SELECT rowid,* FROM mm_entries WHERE strongs LIKE 'G_N/A:%'"))
print(f"N/A entries: {len(na)}")

keyable = []
truly_na = []
for r in na:
    lem = r["lemma_greek"]
    cands = set()
    for v in variants_of_lemma(lem):
        k = norm(v)
        if k in rev:
            cands |= rev[k]
    if cands:
        keyable.append((r["rowid"], lem, sorted(cands)))
    else:
        truly_na.append((r["rowid"], lem))

print(f"\n=== KEYABLE BUT LEFT N/A: {len(keyable)} ===")
for rid, lem, c2 in keyable:
    print(f"  rid={rid}  {lem}  -> {c2}")

print(f"\n=== genuinely not in Strong's index: {len(truly_na)} ===")
for rid, lem in truly_na:
    print(f"  rid={rid}  {lem}")
