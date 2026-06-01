# Moulton-Milligan Digitization — Report

Generated: 2026-06-01T18:20:20.510627+00:00

## Scope of this export

**Lexicon-body chunk** — pages 31–150 (120 pages parsed).
Phase 4 (citation normalization) is skipped for this preview; `papyri_citations`
field holds the raw as-written strings from `papyri_citations_raw`. Phase 5
(disagreement resolution) has run deterministic auto-policies + manual sweeps;
remaining cases requiring human judgment are surfaced in `disagreements_manual.tsv`.

This export uses the **relaxed filter** (all entries included).
Pass `--strict` to apply spec §6's `needs_review=0` filter (299
entries would be excluded).

## Source coverage

- Total source pages: 735
- Parsed pages: 120 (range 31–150)
- Pages still on Tesseract baseline (need Phase 1B): 416

## Entries

- Total entries: 901
- `needs_review=1` flagged: 299
- Placeholder lemmas (`??`): 1
- Exported to mm.sqlite: 828
- Duplicate (strongs, lemma) skipped: 73

## Strong's keying (Phase 3)

- Strong's-keyed: 873 (96.9%)
- `G_N/A:<lemma>` placeholders: 28
- Fuzzy snap corrections (logged in disagreements): 15

Spec §8 gate: ≥75% Strong's coverage — **PASS**.

## Adversarial review (Codex)

- agree: 734 (81.5%)
- minor: 62 (6.9%)
- major: 105 (11.7%)
- reject: 0

agree+minor rate: **88.3%** (spec §8 gate: ≥85%) — **PASS**.

## Phase 5 disagreement resolution

- Resolved: **223** (auto-policies)
- Remaining manual queue: **0** (see `disagreements_manual.tsv`)

Auto-resolution breakdown:
- `auto:accept-reviewer-note` — 57
- `auto:producer-superset-citations` — 12
- `auto:summary-diff-not-content` — 10
- `auto:reviewer-superset-citations` — 9
- `auto:lemma-strip-period` — 7
- `auto:has-translation-from-body` — 7
- `auto:set-equal-keep-producer` — 1

## Files in this export

- `mm.sqlite` — primary deliverable, GRDB.swift-compatible
- `mm.jsonl` — one entry per line
- `mm.tsv` — tab-separated, STEPBible-style header
- `disagreements_manual.tsv` — residual Phase 5 queue (rows needing human judgment)
- `report.md` — this file

## Known limitations

1. Pages 1–30 (front matter + abbreviation tables) NOT parsed.
2. Pages 151–735 NOT parsed (Phase 2 continues over time).
3. `papyri_citations` is raw-as-written, not normalized (Phase 4 unskipped).
4. 0 disagreements remain in the manual queue (Phase 5 partial).
5. Continuation-from-prior-page entries sometimes have inferred lemma rather
   than the true prior-page headword. See entries with
   `notes: "continuation from prior page"`.
