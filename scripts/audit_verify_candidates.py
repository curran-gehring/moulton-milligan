import json, sqlite3, sys, unicodedata, re
sys.stdout.reconfigure(encoding="utf-8")
idx = json.load(open("reference/strongs_lemma_index.json", encoding="utf-8"))

def sa(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch)!="Mn")
def norm(s):
    s = sa(s).lower().replace("ς","σ")
    return re.sub(r"[^α-ω]","",s)

cands = {
 24:["G0041","G0042"],29:["G0048","G0049"],47:["G20014"],371:["G0484"],
 708:["G0891"],766:["G6675"],1495:["G1826"],1665:["G7464"],1852:["G2252"],
 3846:["G4597"],3848:["G9074"],
}
c=sqlite3.connect("out/mm.sqlite"); c.row_factory=sqlite3.Row
for rid,ids in cands.items():
    r=c.execute("SELECT lemma_greek FROM mm_entries WHERE rowid=?",(rid,)).fetchone()
    print(f"\nrid={rid}  MM lemma: {r['lemma_greek']}   (norm pieces: {[norm(p) for p in re.split(r'[ ,]',re.sub(r'[()]','',r['lemma_greek'])) if norm(p)]})")
    for sid in ids:
        o=idx.get(sid) or idx.get(sid.replace('G','G').zfill(0))
        if not o:
            # try alt zero-padding
            for k in idx:
                if k.lstrip('G0')==sid.lstrip('G0'):
                    o=idx[k]; sid=k; break
        if o:
            print(f"    {sid}: lemma={o.get('lemma')}  translit={o.get('translit')}  variants={o.get('variants')}")
        else:
            print(f"    {sid}: NOT FOUND in index")
