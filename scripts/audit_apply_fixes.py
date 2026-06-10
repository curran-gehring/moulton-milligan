"""Apply audit fixes to canonical state/run.sqlite. Transactional + asserted.

All fixes verified by direct vision inspection of the source page scans
(2026-06-09 audit). Run scripts/phase6_export.py afterward to regenerate out/.
"""
import sqlite3, json, sys
sys.stdout.reconfigure(encoding="utf-8")

idx = json.load(open("reference/strongs_lemma_index.json", encoding="utf-8"))
def translit_for(sid):
    o = idx.get(sid)
    return o.get("translit") if o else None

c = sqlite3.connect("state/run.sqlite")
c.execute("BEGIN")

def body(i):
    return c.execute("SELECT body_markdown FROM entries WHERE id=?", (i,)).fetchone()[0]

def replace_in_body(i, old, new, n_expected=1):
    b = body(i)
    cnt = b.count(old)
    assert cnt == n_expected, f"id {i}: expected {n_expected} of {old!r}, found {cnt}"
    c.execute("UPDATE entries SET body_markdown=? WHERE id=?", (b.replace(old, new), i))

def set_lemma(i, old, new):
    cur = c.execute("SELECT lemma_greek FROM entries WHERE id=?", (i,)).fetchone()[0]
    assert cur == old, f"id {i}: lemma is {cur!r} not {old!r}"
    c.execute("UPDATE entries SET lemma_greek=? WHERE id=?", (new, i))

def set_translit(i, new):
    c.execute("UPDATE entries SET lemma_translit=? WHERE id=?", (new, i))

def set_strongs(i, sid, expect_lemma):
    row = c.execute("SELECT lemma_greek, strongs FROM entries WHERE id=?", (i,)).fetchone()
    assert row is not None, f"id {i} missing"
    assert row[0] == expect_lemma, f"id {i}: lemma {row[0]!r} != {expect_lemma!r}"
    assert row[1] is None, f"id {i}: strongs already {row[1]!r}"
    c.execute("UPDATE entries SET strongs=?, lemma_translit=COALESCE(lemma_translit,?) WHERE id=?",
              (sid, translit_for(sid), i))

# ---- CONTENT (OCR) fixes ----
# p110 ἀρτιγέννητος: hallucinated Greek for English "Peter's adj."
replace_in_body(707, "ἀ. δή]", "Peter's adj.")
# p155 γεωργός: hallucinated Greek for Latin "quinquiens"; citation superscripts; γιωργός typo
replace_in_body(1013, "γεωδρομεῖσιν", "*quinquiens*")
replace_in_body(1013, "531⁹", "531⁴⁰")
replace_in_body(1013, "647²⁹", "647²⁰")
replace_in_body(1013, "γιωργός", "γεωργός")
# p300 ἐχθρός: citation superscript misread
replace_in_body(2082, "383⁸⁶", "383²³⁷")
# p300 ἕως: wrong papyrus number + date
replace_in_body(2085, "115¹³ (A.D. 101)", "118¹² (A.D. 110)")

# ---- LEMMA fix ----
# p420: source headword + body both single-σ; stored double-σ is wrong
set_lemma(2964, "μασσάομαι", "μασάομαι")
set_translit(2964, "masáomai")

# ---- DELETE spurious placeholder entry ----
# p603 σiαγόνιον "(See note.)": not a headword on the page (verified against scan)
assert body(4334).strip() == "(See note.)", "id 4334 body changed; abort delete"
c.execute("DELETE FROM reviews WHERE entry_id=4334")
c.execute("DELETE FROM disagreements WHERE entry_id=4334")
c.execute("DELETE FROM entries WHERE id=4334")

# ---- STRONG'S keying (normalization gap: comma-alternates + (μ) optional letters) ----
set_strongs(105,  "G0041",  "ἁγιότης, ἁγιωσύνη")
set_strongs(110,  "G0048",  "ἁγνίζω, ἁγνισμός")
set_strongs(131,  "G20014", "ἀγυιά")
set_strongs(481,  "G0484",  "ἀντίλη(μ)ψις")
set_strongs(852,  "G0891",  "ἄχρι, ἄχρις")
set_strongs(916,  "G6675",  "βίκος")
set_strongs(1909, "G7464",  "ἐπὶ τὸ αὐτό")

c.execute("COMMIT")
print("All fixes applied and committed.")
print("entries now:", c.execute("SELECT COUNT(*) FROM entries").fetchone()[0])
print("G_N/A remaining:", c.execute("SELECT COUNT(*) FROM entries WHERE strongs IS NULL").fetchone()[0])
