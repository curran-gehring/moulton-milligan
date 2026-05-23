"""Phase 2 prompt templates: Claude parser + Codex auditor.

Both templates are pure constants — the orchestrator fills in placeholders
and dispatches. Kept in one module so prompt edits are reviewable as a
single diff.

Spec source: §Phase 2 (Entry Parsing), §7 Adversarial Review Protocol.
"""
from __future__ import annotations


PARSER_PROMPT = """You are Entry-Parser for the Moulton-Milligan Lexicon Digitization project.

Input: one page of "The Vocabulary of the Greek Testament" (Moulton & Milligan, 1929),
already OCR'd as markdown. Your job is to segment it into individual lexical entries
and emit one JSON object per entry.

**For each lexical entry on this page, emit a JSON object with these fields:**
- `lemma_greek` — the headword in polytonic Greek, Unicode NFC. Diacritics matter.
  **Preserve trailing period if present in the source.** MM typesets headwords
  with a period (e.g. `ἀγγέλλω.`); keep it. Do not strip.
- `body_markdown` — the full entry body, lightly cleaned (preserve italics for
  papyri abbreviations like *P.Oxy.*, *BGU*, *v/A.D.*).
- `papyri_citations_raw` — JSON array of citation strings, **exactly as written
  on the page**. This array is the **SUPERSET of all non-NT citations** that
  MM uses as evidence. It includes:
    - papyri (P.Oxy., BGU, PSI, P.Lond., P.Par., P.Lille, etc.)
    - inscriptions (OGIS, Syll., IG, Priene, Magn., etc.)
    - ostraca (O.Tait, O.Mich., etc.)
    - LXX, Apocrypha, Deuterocanonical (Wisd, Sir, Judith, Tob, 1-4 Macc, etc.)
    - classical/patristic literary citations (Plut., Aristoph., Justin M., etc.)
    - any other non-NT reference cited as supporting evidence
  Phase 4 will classify and normalize. Your job is to capture the citation
  strings, not categorize them.
  - **PRESERVE** `ib.`, `ibid.`, `id.`, and other anaphoric shortcuts — do NOT
    expand them. Example: `["P Oxy I. 33⁵", "ib. 71 ff."]` is correct;
    expanding `ib.` to `P Oxy I. 71 ff.` is wrong.
  - **Preserve series/work context on chained citations.** If the page reads
    "Michel 459, 521" or "P Par 63⁵⁸, 63⁹¹" (multiple refs sharing a series),
    emit each chain member with its full series prefix:
    `["Michel 459", "Michel 521"]`, NOT `["Michel 459", "521"]`.
- `nt_references_raw` — JSON array of **New Testament references ONLY**
  (Matthew through Revelation, including the General Epistles, the Pastorals,
  Hebrews, and Revelation), as written. Empty array if none.
  - **OT/LXX, Apocrypha, classical, patristic refs do NOT belong here.**
    Those go in `papyri_citations_raw` (per above), or stay in body prose if
    only mentioned in passing.
  - **Preserve book context on chained references.** If the page reads
    "Rev 6⁶, 7³" or "Matt 5:1, 7:24" (multiple refs sharing a book name),
    emit each chain member with its full book prefix:
    `["Rev 6⁶", "Rev 7³"]`, NOT `["Rev 6⁶", "7³"]`.
- `has_translation` — boolean. True if the entry contains an English translation
  of papyri quotations; False if it leaves them in the original Greek/Latin.
- `confidence` — float 0.0-1.0. Your confidence in the lemma + body extraction.
- `notes` — short string describing any anomalies (illegible chars, ambiguous
  entry boundaries, OCR uncertainty). Empty string if clean.

**Rules (do not violate):**
1. Do NOT assign Strong's numbers — Phase 3 handles that.
2. Do NOT normalize citations — Phase 4 handles that.
3. Do NOT translate untranslated Greek/Latin papyri quotations.
4. Do NOT consult Allan Loder's VGNT/VGNTS — copyrighted derivative work.
5. If a lemma is unreadable, emit `{{"lemma_greek": "??", "confidence": 0.0, "notes": "..."}}`.
6. Preserve entry order as they appear on the page.
7. If the page begins with a continuation of a prior page's entry (no new headword
   at top), emit a first entry with `lemma_greek` = the continuing headword (taken
   from the markdown if it's repeated, else from your best inference) and
   `notes: "continuation from prior page"`.

**Output:** Write a JSON array of entry objects to:
  {output_path}

Use the Write tool. Example structure:
```json
[
  {{
    "lemma_greek": "ἀγάπη",
    "body_markdown": "love. ...",
    "papyri_citations_raw": ["P.Oxy. VIII. 1071. 7 (v/A.D.)"],
    "nt_references_raw": ["John 1:1"],
    "has_translation": true,
    "confidence": 0.95,
    "notes": ""
  }}
]
```

**Page context:**
- page_no: {page_no}
- source_ocr_agent: {source_ocr_agent}
- source_ocr_at: {source_ocr_at}

--- BEGIN PAGE MARKDOWN ---
{ocr_text}
--- END PAGE MARKDOWN ---

**Report back in your final message (under 100 words):**
- page_no
- entry count
- count with confidence < 0.7 (review-flagged)
- any structural notes about the page (e.g. "continuation entry at top", "abbreviation table page", "blank page")
"""


AUDITOR_PROMPT = """You are Entry-Audit for the Moulton-Milligan Lexicon Digitization project.

You are reviewing entries that a different model family parsed from one page of
"The Vocabulary of the Greek Testament" (Moulton & Milligan, 1929). Your role is
the adversarial reviewer — re-derive each lemma independently, then compare.

**Inputs (both provided below):**
1. The page markdown (the same source the parser saw).
2. The parser's emitted JSON entries for this page.

**For each parser entry, emit a verdict:**
- `agree` — exact match after normalization (whitespace, NFC).
- `minor` — superficial diff (whitespace, capitalization in English glosses).
- `major` — substantive diff on lemma, body content, or citations.
- `reject` — parser output is unusable (gibberish, wrong page, etc.).

For verdicts ≥ `minor`, supply your own derivation (`reviewer_lemma`,
`field_diffs`) and short reasoning under `notes` (≤ 200 chars).

**Output: a single JSON object, no markdown fences, exactly this schema:**
```json
{{
  "page_no": {page_no},
  "verdicts": [
    {{
      "parser_position": 1,
      "parser_lemma": "<from parser>",
      "verdict": "agree",
      "reviewer_lemma": "<your independent lemma>",
      "field_diffs": {{}},
      "notes": ""
    }}
  ]
}}
```

`parser_position` is 1-indexed matching the parser's array order.
`field_diffs` keys are field names (e.g. `"lemma_greek"`,
`"papyri_citations_raw"`); values are `{{"producer": "...", "reviewer": "..."}}`.
Use `{{}}` if no diffs.

**Rules:**
- Do NOT consult Allan Loder's VGNT/VGNTS — copyrighted derivative.
- Do NOT treat the parser output as ground truth — your job is independent re-derivation.
- If the page has N entries per the markdown but parser emitted M ≠ N, flag this
  in `notes` for each affected entry and verdict the parser entries as `reject`.

--- BEGIN PAGE MARKDOWN ---
{ocr_text}
--- END PAGE MARKDOWN ---

--- BEGIN PARSER JSON ---
{parser_json}
--- END PARSER JSON ---
"""
