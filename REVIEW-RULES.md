# moulton-milligan review rules

Sent to the adversarial review lenses when a diff touches a matching path. Each rule records a defect that shipped or was caught once. Add a rule when a reviewer could have seen the defect in the diff.

## Strong's keying
paths: scripts/phase3_*

- A fuzzy snap of a lemma to a Strong's entry is kept only for a same-lexeme variant (inflection, breathing, accent, mu-pi or nu-gamma spelling). A different prefix or stem is almost always wrong and sets `G_N/A` (NULL): apopipto snapped to a participle key, a coincidental porne snap, deilaugos to teilaugos.
- NT text is tagged with classic numbers, so a homograph lemma resolves to the classic id (at most G5624) and drops extended ids (above G5624) when a classic one exists; an extended key orphans the entry. `phase3_disambiguate_homographs.py` runs after each phase 3 wave, and a snap-audit rerun must not flip decisions already kept (the audit is not deterministic).

## Reparse and dispute resolution
paths: scripts/phase2_writer.py scripts/phase2_dispatch.py scripts/phase5_resolve.py scripts/migrate_v2.py

- A reparse after an OCR upgrade (`entries.source_ocr_agent` differs from `pages.ocr_agent`) cascade-deletes the page's entries and their reviews and disagreements before inserting the new rows, so no stale disagreement points at a deleted entry.
- A Phase 5 policy writes to `entries` only when it changes a value; a keep-producer decision just closes the disagreement row, which preserves `source_ocr_at`.
- Set-superset resolution (keep the side with more items) is safe only for papyri citations. Applying it to `nt_references_raw` would keep wrong references, because each NT reference is a claim to verify (the longer alpha-privative list included lemmas for different Greek words). The auditor sometimes returns descriptions of a difference (`ASCII quotation punctuation`) instead of text; such `field_diffs` are not content disputes.
