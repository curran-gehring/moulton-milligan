# Moulton-Milligan Digitization — Report

Generated: 2026-06-02T13:34:13.153225+00:00

## Scope of this export

**Lexicon-body chunk** — pages 31–360 (328 pages parsed).
Phase 4 (citation normalization) is skipped for this preview; `papyri_citations`
field holds the raw as-written strings from `papyri_citations_raw`. Phase 5
(disagreement resolution) has run deterministic auto-policies + manual sweeps;
remaining cases requiring human judgment are surfaced in `disagreements_manual.tsv`.

This export uses the **relaxed filter** (all entries included).
Pass `--strict` to apply spec §6's `needs_review=0` filter (850
entries would be excluded).

## Source coverage

- Total source pages: 735
- Parsed pages: 328 (range 31–360)
- Pages still on Tesseract baseline (need Phase 1B): 376

## Entries

- Total entries: 2415
- `needs_review=1` flagged: 850
- Placeholder lemmas (`??`): 1
- Exported to mm.sqlite: 2198
- Duplicate (strongs, lemma) skipped: 217

## Strong's keying (Phase 3)

- Strong's-keyed: 2364 (97.9%)
- `G_N/A:<lemma>` placeholders: 51
- Fuzzy snap corrections (logged in disagreements): 42

Spec §8 gate: ≥75% Strong's coverage — **PASS**.

## Adversarial review (Codex)

- agree: 1935 (80.1%)
- minor: 171 (7.1%)
- major: 309 (12.8%)
- reject: 0

agree+minor rate: **87.2%** (spec §8 gate: ≥85%) — **PASS**.

## Phase 5 disagreement resolution

- Resolved: **699** (auto-policies)
- Remaining manual queue: **0** (see `disagreements_manual.tsv`)

Auto-resolution breakdown:
- `auto:accept-reviewer-note` — 189
- `auto:has-translation-from-body` — 44
- `auto:producer-superset-citations` — 32
- `auto:reviewer-superset-citations` — 31
- `auto:summary-diff-not-content` — 11
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
2. Pages 361–735 NOT parsed (Phase 2 continues over time).
3. `papyri_citations` is raw-as-written, not normalized (Phase 4 unskipped).
4. 0 disagreements remain in the manual queue (Phase 5 partial).
5. Continuation-from-prior-page entries sometimes have inferred lemma rather
   than the true prior-page headword. See entries with
   `notes: "continuation from prior page"`.
