# Phase 2 — Entry Parsing & Adversarial Review

Phase 2 is driven by the Claude Code orchestrator (the main session), not a
single Python script. Python pieces handle the deterministic edges (state
queries, file IO, Codex subprocess); Claude sub-agents do the parsing.

## One wave

```
1. python scripts/phase2_dispatch.py --first 10 --out tmp/parse/dispatch.json
   (manifest of up-to-10 pages ready to parse)

2. mkdir -p tmp/parse
   For each page in the manifest, spawn one Claude Task sub-agent with
   PARSER_PROMPT from scripts/phase2_prompts.py filled in. Sub-agent
   writes tmp/parse/page-NNN.json (JSON array of entries).

3. python scripts/phase2_writer.py --batch tmp/parse/
   Ingests parser output into entries table. Idempotent: drops prior
   entries/reviews/disagreements for each page before re-inserting.

4. python scripts/phase2_audit.py --pages <comma-list>
   Or: python scripts/phase2_audit.py --all-unaudited --first 10
   Calls Codex via codex_call.py per page; writes reviews + disagreements.

5. python scripts/phase2_status.py
   Snapshot: parsed pages, entries by confidence, codex verdict breakdown,
   open disagreements, reparse backlog.
```

## Reparse-on-OCR-upgrade

When a page's OCR upgrades from `tesseract` to `claude-vision` after Phase 2
already parsed entries from the Tesseract baseline:

- `phase2_dispatch.py` automatically includes that page in its next manifest
  with `reparse: true`.
- `phase2_writer.py` deletes the old entries (and their reviews/disagreements)
  before inserting the new parse.
- Net effect: back-half quality silently upgrades as Phase 1B continues in
  the background.

No manual intervention; just keep running waves.

## Pacing

- One parser sub-agent per page. 4-10 in parallel is comfortable; 8 matches the
  Phase 1B convention.
- Each parser wave plus audit is ~5-15 min wall-clock depending on page density.
- Stop when monthly Max-plan throttle lands; resume next session — state DB
  is the source of truth, no information loss.

## Quality gates (spec §8)

After each wave:
- Strong's coverage isn't measurable until Phase 3, but
- Entry parser agreement rate (`agree+minor` in codex reviews) should hold ≥ 85%.
  If below, inspect divergent pages and refine PARSER_PROMPT before continuing.

## Files

| Script | Role |
|---|---|
| `phase2_prompts.py` | PARSER_PROMPT, AUDITOR_PROMPT constants |
| `phase2_dispatch.py` | Pick next pages → emit JSON manifest |
| `phase2_writer.py` | Ingest parser output → entries table (idempotent) |
| `phase2_audit.py` | Run Codex auditor → reviews + disagreements |
| `phase2_status.py` | Snapshot Phase 2 progress |
| `codex_call.py` | Subprocess wrapper around `codex exec` (pre-existing) |
