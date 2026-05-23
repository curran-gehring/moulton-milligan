# Moulton-Milligan Digitization — Report

Generated: 2026-05-23T12:05:37.383814+00:00

## Scope of this export

**Alpha-chunk preview** — pages 31–80 only (first ~50 lexicon-body pages).
Phase 4 (citation normalization) and Phase 5 (disagreement resolution) are
**skipped** for this preview; `papyri_citations` field holds the raw
as-written strings from `papyri_citations_raw`.

This export uses the **relaxed filter** (all entries included).
Pass `--strict` to apply spec §6's `needs_review=0` filter (120
entries would be excluded).

## Source coverage

- Total source pages: 735
- Parsed pages: 50
- Pages still on Tesseract baseline (need Phase 1B): 416

## Entries

- Total entries: 425
- `needs_review=1` flagged: 120
- Placeholder lemmas (`??`): 4
- Exported to mm.sqlite: 395
- Duplicate (strongs, lemma) skipped: 30

## Strong's keying (Phase 3)

- Strong's-keyed: 410 (96.5%)
- `G_N/A:<lemma>` placeholders: 15
- Fuzzy snap corrections (logged in disagreements): 10

Spec §8 gate: ≥75% Strong's coverage — **PASS**.

## Adversarial review (Codex)

- agree: 342 (80.5%)
- minor: 36 (8.5%)
- major: 47 (11.1%)
- reject: 0

agree+minor rate: **88.9%** (spec §8 gate: ≥85%) — **PASS**.

Open disagreements (Phase 5 work): **98**.

## Files in this export

- `mm.sqlite` — primary deliverable, GRDB.swift-compatible
- `mm.jsonl` — one entry per line
- `mm.tsv` — tab-separated, STEPBible-style header
- `report.md` — this file

## Known limitations

1. Pages 1–30 (front matter + abbreviation tables) NOT parsed.
2. Pages 81–735 NOT parsed (Phase 2 continues over time).
3. `papyri_citations` is raw-as-written, not normalized (Phase 4 unskipped).
4. 98 open disagreements not resolved (Phase 5 unskipped).
5. Continuation-from-prior-page entries sometimes have inferred lemma rather
   than the true prior-page headword. See entries with
   `notes: "continuation from prior page"`.
