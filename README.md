# Moulton-Milligan Lexicon Digitization

Multi-agent workflow producing a Strong's-keyed digitization of *The Vocabulary
of the Greek Testament* (Moulton & Milligan, 1929) from public-domain scans.

Spec: `OneDrive - Tucker Milling LLC/moulton-milligan-digitization.pdf` — read
before resuming work.

## Status

State of record is `state/run.sqlite`. Check the `meta` table for the most
recent pause/checkpoint note. Counts via:

```sh
python -c "import sqlite3; c=sqlite3.connect('state/run.sqlite'); \
  print('vision:', c.execute(\"SELECT COUNT(*) FROM pages WHERE ocr_agent='claude-vision'\").fetchone()[0]); \
  print('tesseract only:', c.execute(\"SELECT COUNT(*) FROM pages WHERE ocr_agent='tesseract'\").fetchone()[0]); \
  print('entries:', c.execute('SELECT COUNT(*) FROM entries').fetchone()[0])"
```

## Layout

| Path | Tracked | Purpose |
|---|---|---|
| `scripts/` | yes | Pipeline orchestration (Phase 1A/B, writer, Codex bridge) |
| `state/run.sqlite` | yes | Canonical state (pages, entries, reviews, disagreements, meta) |
| `pages/*.txt` | yes | Tesseract baseline OCR (Phase 1A) |
| `pages/*.vision.md` | yes | Claude vision OCR markdown (Phase 1B) |
| `reference/strongs_lemma_index.json` | yes | Built snap-target for Phase 3 |
| `pages/*.png` | **no** | 305 MB; regenerate from `source/mm-1929.pdf` |
| `source/*.pdf` | **no** | 104 MB; see "Acquiring sources" below |
| `reference/{strongs,stepbible,sblgnt}/` | **no** | 522 MB; clones, see below |
| `tmp/` | **no** | Sub-agent scratch output |

## Acquiring sources (fresh checkout)

```sh
# 1. Source PDF
mkdir -p source pages reference
curl -L -o source/mm-1929.pdf \
  "https://archive.org/download/moulton-milligan-the-vocabulary-of-the-greek-testament-hodder-stoughton-1914-1929-735pp-new-lz/moulton-milligan-the-vocabulary-of-the-greek-testament-hodder-stoughton-1914-1929-735pp-new-lz.pdf"

# 2. Rasterize (300 dpi)
pdftoppm -r 300 -png source/mm-1929.pdf pages/page

# 3. Reference repos
cd reference
git clone --depth 1 https://github.com/openscriptures/strongs.git
git clone --depth 1 https://github.com/STEPBible/STEPBible-Data.git stepbible
git clone --depth 1 https://github.com/morphgnt/sblgnt.git
cd ..
```

## Hard constraints

- No API keys. Only `claude` (Code subscription) and `codex` (CLI subscription).
- Do not consult Allan Loder's VGNT/VGNTS — copyrighted derivative work.
- Do not translate untranslated Greek/Latin papyri quotations.
- Same-family adversarial review is forbidden (Claude → reviewed by Codex; Codex → reviewed by Claude).
