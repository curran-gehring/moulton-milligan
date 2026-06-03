# Moulton-Milligan Digitization — Report

Generated: 2026-06-03T03:26:06.240546+00:00

## Scope of this export

**Lexicon-body chunk** — pages 31–560 (525 pages parsed).
Phase 4 (citation normalization) is skipped for this preview; `papyri_citations`
field holds the raw as-written strings from `papyri_citations_raw`. Phase 5
(disagreement resolution) has run deterministic auto-policies + manual sweeps;
remaining cases requiring human judgment are surfaced in `disagreements_manual.tsv`.

This export uses the **relaxed filter** (all entries included).
Pass `--strict` to apply spec §6's `needs_review=0` filter (1324
entries would be excluded).

## Source coverage

- Total source pages: 735
- Parsed pages: 525 (range 31–560)
- Pages still on Tesseract baseline (need Phase 1B): 176

## Entries

- Total entries: 3791
- `needs_review=1` flagged: 1324
- Placeholder lemmas (`??`): 1
- Exported to mm.sqlite: 3527
- Duplicate (strongs, lemma) skipped: 264

## Strong's keying (Phase 3)

- Strong's-keyed: 3737 (98.6%)
- `G_N/A:<lemma>` placeholders: 54
- Fuzzy snap corrections (logged in disagreements): 91

Spec §8 gate: ≥75% Strong's coverage — **PASS**.

## Adversarial review (Codex)

- agree: 3048 (80.4%)
- minor: 266 (7.0%)
- major: 456 (12.0%)
- reject: 0

agree+minor rate: **87.4%** (spec §8 gate: ≥85%) — **PASS**.

## Phase 5 disagreement resolution

- Resolved: **1029** (auto-policies)
- Remaining manual queue: **0** (see `disagreements_manual.tsv`)

Auto-resolution breakdown:
- `auto:accept-reviewer-note` — 225
- `auto:has-translation-from-body` — 112
- `auto:reviewer-superset-citations` — 44
- `auto:producer-superset-citations` — 44
- `auto:summary-diff-not-content` — 14
- `auto:lemma-strip-period` — 7
- `auto:set-equal-keep-producer` — 1

## Files in this export

- `mm.sqlite` — primary deliverable, GRDB.swift-compatible
- `mm.jsonl` — one entry per line
- `mm.tsv` — tab-separated, STEPBible-style header
- `disagreements_manual.tsv` — residual Phase 5 queue (rows needing human judgment)
- `report.md` — this file

## Known limitations

1. Pages 1–30 (front matter + abbreviation tables) NOT parsed.
2. Pages 561–735 NOT parsed (Phase 2 continues over time).
3. `papyri_citations` is raw-as-written, not normalized (Phase 4 unskipped).
4. 0 disagreements remain in the manual queue (Phase 5 partial).
5. Continuation-from-prior-page entries sometimes have inferred lemma rather
   than the true prior-page headword. See entries with
   `notes: "continuation from prior page"`.
