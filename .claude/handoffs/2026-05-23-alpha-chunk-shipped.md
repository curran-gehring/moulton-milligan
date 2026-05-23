# Session Handoff: MM alpha chunk shipped (pages 31–80)

**Date:** 2026-05-23
**Project:** `C:\Dev\moulton-milligan`
**Session length:** Long single session, 9 commits (`d0bbbb3` → `371166f`)

## Current state

- **Task:** Resume Moulton-Milligan digitization (paused 2026-04-26 at 313/735 Phase 1B). Reach a working `mm.sqlite` for FirstWord integration preview.
- **Phase:** Phase 6 complete for pages 31–80 chunk.
- **Progress:** 50 / 735 pages parsed (6.8%). Alpha-chunk deliverable (`out/mm.sqlite` + jsonl/tsv/report) ready as preview. **Both spec §8 gates pass: 96.5% Strong's coverage / 88.9% agree+minor.**

## What this session accomplished

1. Set up git in the project for the first time (1059-file initial commit + 8 follow-ups).
2. Wired the schema v1→v2 migration to support reparse-on-OCR-upgrade (Plan C interleaving).
3. Phase 1B remediation on 6 of 7 stragglers (319/735 vision-OCR'd; page 11 permanently filter-skipped).
4. Built the full Phase 2 rig from scratch (parser + auditor prompts, dispatch, writer, audit, status scripts, README).
5. Ran 5 Phase 2 waves on pages 31–80 (50 pages, 425 entries, 100% Codex audit coverage).
6. Wrote Phase 3 (Strong's keying via rapidfuzz) and Phase 6 (mm.sqlite/jsonl/tsv/report export).
7. Logged learnings + updated knowledge base + updated project memory.

## Key decisions

- **Plan C (interleave Phase 2 with remaining Phase 1B) over sequential** — justified only because reparse-on-OCR-upgrade is wired. Mechanism: `entries.source_ocr_agent` + `entries.source_ocr_at` columns, idempotent writer cascade-deletes on reparse.
- **Stopped prompt refinement at wave 2 of three** — wave 3 over-corrected. Codex's audit signal has a noise floor at stylistic edge cases; further per-pattern tuning yields diminishing returns. Phase 5 disagreement resolution is the right home for those.
- **"Read this file" sub-agent pattern over inline OCR text** — smaller prompts, easier to dispatch 10 in parallel without context bloat.
- **Skipped Phase 4 (citation normalization) and Phase 5 (disagreement resolution) for the preview** — papyri_citations field contains raw-as-written strings. 98 open disagreements queued. Documented in `out/report.md`.
- **Longest-body wins on (strongs, lemma) dedup** in Phase 6 — continuation entries on next page often have the fuller body than truncated start; first-seen-wins would clip.
- **AUDITOR_PROMPT tweaked mid-session** to recognize legitimate continuation entries (was rejecting all 9 entries on page 45 because of count mismatch).

## Code added (all in `scripts/`)

| File | Purpose |
|---|---|
| `migrate_v2.py` | Idempotent schema v1→v2 (already applied) |
| `phase2_prompts.py` | PARSER_PROMPT v2 + AUDITOR_PROMPT (canonical) |
| `phase2_dispatch.py` | Page-manifest emitter; auto-includes reparse candidates |
| `phase2_writer.py` | Idempotent entries ingest; cascade-deletes reviews + disagreements on reparse |
| `phase2_audit.py` | Codex audit per page → writes `reviews` + `disagreements` |
| `phase2_status.py` | One-shot progress snapshot (no args) |
| `phase3_strongs.py` | Strong's keying via rapidfuzz (Levenshtein ≤ 2) |
| `phase6_export.py` | Final export to `out/mm.sqlite|jsonl|tsv|report.md` |
| `README_phase2.md` | Orchestration recipe for waves |

## Deliverables (committed in `out/`)

```
mm.sqlite       548 KB    395 unique entries (383 Strong's-keyed, 12 G_N/A)
mm.jsonl        508 KB    one entry per line
mm.tsv          450 KB    STEPBible-style with header row
report.md       2 KB      coverage stats + known limitations
```

Sample lookups verified working:
```
ἀβαρής   → G0004  (abarḗs)    page 31    415 chars
ἀγάπη    → G0026  (agápē)     page 32   3240 chars
ἀγαπάω   → G0025  (agapáō)    page 31   1792 chars
ἅγιος    → G0040  (hágios)    page 34    549 chars
ἀδελφός  → G0080  (adelphós)  page 38    286 chars
ᾅδης     → G0086  (háidēs)    page 39    964 chars
```

## Open questions

- [ ] Continue Phase 2 scale (pages 81+) OR jump to FirstWord client integration with the current 395-entry deliverable?
- [ ] FirstWord bundling: ship `mm.sqlite` inside the app bundle, or download from R2 like the existing interlinear DB does?
- [ ] When to drive Phase 1B catch-up for pages 321–735 vs continuing Phase 2 on the 269 already-vision-OCR'd pages?
- [ ] Continuation-entry lemma misidentification — parser sometimes infers wrong lemma when page opens mid-entry. Fix requires giving parser prior-page context (small dispatch change). Worth doing before scaling?

## Blockers / known issues

- **Page 11 permanently filter-skipped.** API content filter blocks vision OCR every retry. Accepted Tesseract baseline; resolution recorded in `meta.page_11_filter_resolution`.
- **98 open disagreements** queued in `disagreements` table. Phase 5 work. Not blocking; not resolved.
- **Codex audit signal flips across runs** on stylistic edge cases (LXX/Apocrypha placement, trailing periods on lemmas). Documented in commit `4a66e97` and in `learnings/2026-05.md`. Don't over-iterate prompt.
- **Token budget unknown.** April pause hit Max-plan monthly limit at 313 Phase 1B pages. This session burned ~3M Claude + ~500K Codex tokens on 40 pages of Phase 2. Watch budget before scaling.

## Context to remember

- **Spec PDF** at `C:\Users\CurranGehring\OneDrive - Tucker Milling LLC\moulton-milligan-digitization.pdf` — read end-to-end before any new phase work.
- **State DB at `state/run.sqlite`** is single source of truth, binary-tracked in git. Roll back any wave with `git checkout <sha> -- state/run.sqlite scripts/phase2_prompts.py`.
- **Lexicon body starts at page 31.** Pages 1–30 are front matter (title, preface, intro, abbreviation tables). Pages 1–30 still need parsing eventually — abbreviation tables on pp. 25–30 are required for Phase 4 (citation normalization).
- **Codex CLI** must be installed (`npm install -g @openai/codex`, ChatGPT login). Verify: `node "C:/Users/CurranGehring/.claude/plugins/cache/openai-codex/codex/1.0.3/scripts/codex-companion.mjs" setup --json`.
- **Hard constraints** (per spec, do not violate):
  - No API keys (Claude Code + Codex CLI subscriptions only)
  - No Allan Loder VGNT/VGNTS consultation
  - No translating untranslated Greek/Latin papyri quotations
  - Same-family adversarial review forbidden (Claude → Codex; never Claude → Claude)
- **Curran's stop-rule from this session:** "When a refinement targets a real bug, do it. When it targets a stylistic call that depends on the reviewer's mood, stop."

## Next steps (in priority order)

1. [ ] Run `python scripts/phase2_status.py` to confirm current state (should report: 50 parsed pages, 425 entries, 100% audit coverage, 98 open disagreements, 0 reparse backlog).
2. [ ] Decide: scale Phase 2 (pages 81+) **or** ship FirstWord integration with current chunk.
3. [ ] **If scaling Phase 2:** `python scripts/phase2_dispatch.py --from 81 --to 100 --out tmp/parse/dispatch_e.json`, then dispatch 10 parallel parser sub-agents using the prompt template from waves A–D (see commit `371166f`). Then `phase2_writer.py --batch tmp/parse/`, then `phase2_audit.py --pages 81,...,100`.
4. [ ] **If integrating FirstWord:** scope the work — `mm.sqlite` bundling vs R2 download decision, GRDB query layer for `mm_entries` table, lexicon tab UI, long-press-on-Greek-word handoff from existing scripture view. ~Half-day estimate.
5. [ ] **For final full-735 production:** drive Phase 1B catch-up for the remaining 416 Tesseract-only pages FIRST (token-budget-permitting), then Phase 2 reparse-on-upgrade hook auto-refreshes them.
6. [ ] **Phase 5 (disagreement resolution):** 98 open disagreements. Auto-resolve via Strong's-snap consensus where possible; surface manual queue for the rest. Probably ~1 hour of work.

## Files to read on resume

- `C:\Users\CurranGehring\.claude\projects\C--Dev\memory\project_moulton_milligan.md` — full project memory (updated this session)
- `C:\Dev\moulton-milligan\out\report.md` — alpha chunk coverage stats
- `C:\Dev\moulton-milligan\scripts\README_phase2.md` — Phase 2 wave orchestration recipe
- `C:\Dev\knowledge-base\learnings\2026-05.md` — search "2026-05-23 — Moulton-Milligan" for the three big lessons
- `C:\Dev\moulton-milligan\scripts\phase2_prompts.py` — canonical PARSER_PROMPT v2 + AUDITOR_PROMPT (do NOT refine further without strong evidence)

## Git state

8 commits this session on local-only repo `C:\Dev\moulton-milligan` (no remote configured). Last commit `371166f`. Working tree clean.

To roll back to start of session: `git checkout d0bbbb3`.
To roll back to end of wave 2 (best agree+minor on small chunk): `git checkout ce8ef29`.

Knowledge-base committed + pushed: learnings entry at `5e1a2f3` upstream (tuckermilling/knowledge-base).

## Aborted / dead-end approaches (don't redo these)

- **Wave 3 prompt refinement** (commit `4a66e97`, then reverted in `ce8ef29`): tried generalizing "papyri_citations_raw is the SUPERSET of all non-NT citations including LXX/classical/literary" + trailing-period preservation + papyri series-context. Made things worse — Codex flipped preferences. Reverted to wave 2 prompt. Don't retry without a fundamentally different approach.
- **Adding more `## ` count mismatch strictness to AUDITOR_PROMPT.** Already loosened to recognize continuation entries (commit `371166f`). Tightening it again will cause page-45-style rejection cascades.
