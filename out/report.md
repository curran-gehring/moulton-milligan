# Moulton-Milligan Digitization — Report

Generated: 2026-05-23T13:10:13.812615+00:00

## Scope of this export

**Alpha-chunk preview** — pages 31–80 only (first ~50 lexicon-body pages).
Phase 4 (citation normalization) is skipped for this preview; `papyri_citations`
field holds the raw as-written strings from `papyri_citations_raw`. Phase 5
(disagreement resolution) has run deterministic auto-policies; remaining
cases requiring human judgment are surfaced in `disagreements_manual.tsv`.

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
- Placeholder lemmas (`??`): 1
- Exported to mm.sqlite: 395
- Duplicate (strongs, lemma) skipped: 30

## Strong's keying (Phase 3)

- Strong's-keyed: 412 (96.9%)
- `G_N/A:<lemma>` placeholders: 13
- Fuzzy snap corrections (logged in disagreements): 10

Spec §8 gate: ≥75% Strong's coverage — **PASS**.

## Adversarial review (Codex)

- agree: 342 (80.5%)
- minor: 36 (8.5%)
- major: 47 (11.1%)
- reject: 0

agree+minor rate: **88.9%** (spec §8 gate: ≥85%) — **PASS**.

## Phase 5 disagreement resolution

- Resolved: **109** (auto-policies)
- Remaining manual queue: **0** (see `disagreements_manual.tsv`)

Auto-resolution breakdown:
- `auto:accept-reviewer-note` — 18
- `auto:summary-diff-not-content` — 10
- `auto:producer-superset-citations` — 10
- `auto:lemma-strip-period` — 7
- `auto:reviewer-superset-citations` — 6
- `auto:has-translation-from-body` — 1

## Files in this export

- `mm.sqlite` — primary deliverable, GRDB.swift-compatible
- `mm.jsonl` — one entry per line
- `mm.tsv` — tab-separated, STEPBible-style header
- `disagreements_manual.tsv` — residual Phase 5 queue (rows needing human judgment)
- `report.md` — this file

## Known limitations

1. Pages 1–30 (front matter + abbreviation tables) NOT parsed.
2. Pages 81–735 NOT parsed (Phase 2 continues over time).
3. `papyri_citations` is raw-as-written, not normalized (Phase 4 unskipped).
4. 0 disagreements remain in the manual queue (Phase 5 partial).
5. Continuation-from-prior-page entries sometimes have inferred lemma rather
   than the true prior-page headword. See entries with
   `notes: "continuation from prior page"`.
