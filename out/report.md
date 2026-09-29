# Moulton-Milligan Digitization — Report

Generated: 2026-09-29T14:35:55.023757+00:00

## Scope of this export

**Lexicon-body chunk** — pages 31–735 (695 pages parsed).
Phase 4 (citation normalization) is DONE: `papyri_citations_norm` holds per-citation
objects {raw, norm, series, status} normalized against MM's own front-matter
abbreviation table (reference/papyri_abbreviations.json, 303 entries); ib./id.
anaphora expanded from the preceding citation. `papyri_citations` remains the raw
as-written strings. Phase 5
(disagreement resolution) has run deterministic auto-policies + manual sweeps;
remaining cases requiring human judgment are surfaced in `disagreements_manual.tsv`.

This export uses the **relaxed filter** (all entries included).
Pass `--strict` to apply spec §6's `needs_review=0` filter (1622
entries would be excluded).

## Source coverage

- Total source pages: 735
- Parsed pages: 695 (range 31–735)
- Pages still on Tesseract baseline (need Phase 1B): 1

## Entries

- Total entries: 4803
- `needs_review=1` flagged: 1622
- Placeholder lemmas (`??`): 0
- Exported to mm.sqlite: 4786
- Duplicate (strongs, lemma) skipped: 17

## Strong's keying (Phase 3)

- Strong's-keyed: 4727 (98.4%)
- `G_N/A:<lemma>` placeholders: 76
- Fuzzy snap corrections (logged in disagreements): 108

Spec §8 gate: ≥75% Strong's coverage — **PASS**.

## Adversarial review (Codex)

- agree: 3974 (82.7%)
- minor: 281 (5.9%)
- major: 528 (11.0%)
- reject: 0

agree+minor rate: **88.6%** (spec §8 gate: ≥85%) — **PASS**.

## Phase 5 disagreement resolution

- Resolved: **1179** (auto-policies)
- Remaining manual queue: **0** (see `disagreements_manual.tsv`)

Auto-resolution breakdown:
- `auto:has-translation-from-body` — 294
- `auto:producer-superset-citations` — 61
- `auto:reviewer-superset-citations` — 55
- `auto:accept-reviewer-note` — 35
- `auto:summary-diff-not-content` — 12
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
2. Pages 736–735 NOT parsed (Phase 2 continues over time).
3. `papyri_citations` is raw-as-written; `papyri_citations_norm` is the Phase-4 normalized form.
4. 0 disagreements remain in the manual queue (Phase 5 partial).
5. Continuation-from-prior-page entries sometimes have inferred lemma rather
   than the true prior-page headword. See entries with
   `notes: "continuation from prior page"`.
