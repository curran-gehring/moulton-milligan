"""Phase 3 snap audit (spec §6: Codex review of fuzzy snap-corrections).

Every entry whose Strong's number was assigned by phase3's fuzzy fallback
(rapidfuzz Levenshtein <= 2) carries a `disagreements` row with
`resolution_by='auto:strongs-snap'`. A coincidental edit-distance match can key
a headword to an UNRELATED lexeme (e.g. ἄπορος -> πόρνος, ἀδιάφθορος -> διάφορος).

This script sends every LIVE snap (entry still carries the snapped strongs) to
Codex — a different model family than the producer, per the spec's adversarial
rule — and asks it to verdict each as:
  keep   — same lexeme; differs only by inflection ending / breathing / accent /
           μπ-π Koine spelling / final-ν movable, etc.
  reject — coincidental neighbor; a DIFFERENT lexeme. Revert to G_N/A (NULL).

For each `reject` (unless --dry-run): set entries.strongs=NULL, clear translit,
and write a `manual:strongs-fix` disagreement row. That tag is also phase3's
re-snap guard, so a rejected snap will NOT be re-introduced on the next run.

Usage:
  python scripts/phase3_audit_snaps.py --dry-run
  python scripts/phase3_audit_snaps.py
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from codex_call import codex_exec  # noqa: E402

DB_PATH = ROOT / "state" / "run.sqlite"
INDEX_PATH = ROOT / "reference" / "strongs_lemma_index.json"

JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json_array(text: str):
    if not text:
        return None
    candidates = []
    m = JSON_FENCE.search(text)
    if m:
        candidates.append(m.group(1))
    candidates.append(text)
    first = text.find("[")
    if first >= 0:
        candidates.append(text[first:])
    for c in candidates:
        try:
            v = json.loads(c)
            if isinstance(v, list):
                return v
        except json.JSONDecodeError:
            continue
    return None


PROMPT_HEAD = """You are the adversarial Strong's-key auditor for the Moulton-Milligan lexicon.

A fuzzy matcher (Levenshtein edit-distance <= 2) assigned each Moulton-Milligan
headword below to a Strong's number by snapping it to the nearest lemma in a
Strong's index. Edit-distance can match an UNRELATED word. Your job: for each
item decide whether the snapped Strong's lemma is the SAME Greek lexeme as the
Moulton-Milligan headword.

- verdict "keep"  ONLY if they are the same lexeme differing merely by: inflection
  ending, breathing mark, accent position, μπ/π or other Koine spelling variant,
  movable-ν, or iota-subscript. The snapped lemma may be an inflected/participle
  form of the headword — that still counts as the same lexeme = keep.
- verdict "reject" if they are DIFFERENT lexemes (different root/stem/meaning),
  even if spelled similarly. Examples of reject: ἄπορος ("without means") vs
  πόρνος ("fornicator"); ἀδιάφθορος ("incorruptible") vs διάφορος ("different").

Use the body excerpt only as a tie-breaker for meaning. Do NOT consult Allan
Loder's VGNT. Return ONLY a JSON array, no prose, exactly:
[{"idx": <int>, "verdict": "keep"|"reject", "reason": "<=160 chars"}]

ITEMS:
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout", type=int, default=420)
    args = ap.parse_args()

    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        """
        SELECT DISTINCT e.id, e.page_no, e.lemma_greek, e.strongs, e.body_markdown
          FROM disagreements d
          JOIN entries e ON e.id = d.entry_id
         WHERE d.resolution_by='auto:strongs-snap' AND e.strongs IS NOT NULL
         ORDER BY e.id
        """
    ).fetchall()
    if not rows:
        print("no live snaps to audit")
        return 0

    items = []
    for i, r in enumerate(rows):
        sid = r["strongs"]
        sinfo = idx.get(sid, {})
        items.append({
            "idx": i,
            "entry_id": r["id"],
            "page_no": r["page_no"],
            "mm_headword": r["lemma_greek"],
            "snapped_strongs": sid,
            "strongs_lemma": sinfo.get("lemma"),
            "strongs_translit": sinfo.get("translit"),
            "body_excerpt": (r["body_markdown"] or "")[:200],
        })

    payload = [
        {k: it[k] for k in ("idx", "mm_headword", "snapped_strongs",
                            "strongs_lemma", "strongs_translit", "body_excerpt")}
        for it in items
    ]
    prompt = PROMPT_HEAD + json.dumps(payload, ensure_ascii=False, indent=2)

    print(f"auditing {len(items)} live snap(s) via Codex...")
    raw = codex_exec(prompt, timeout=args.timeout)
    verdicts = extract_json_array(raw or "")
    if not verdicts:
        print("ERROR: could not parse Codex verdicts. Raw head:")
        print((raw or "")[:500])
        return 1

    by_idx = {v.get("idx"): v for v in verdicts if isinstance(v, dict)}
    now = datetime.now(timezone.utc).isoformat()
    kept = rejected = 0

    for it in items:
        v = by_idx.get(it["idx"])
        if not v:
            print(f"  p{it['page_no']} {it['mm_headword']} -> {it['snapped_strongs']}: NO VERDICT (skip)")
            continue
        verdict = (v.get("verdict") or "").lower()
        reason = (v.get("reason") or "")[:160]
        tag = "KEEP " if verdict == "keep" else ("REJECT" if verdict == "reject" else "?????")
        print(f"  [{tag}] p{it['page_no']} {it['mm_headword']} -> {it['snapped_strongs']} "
              f"({it['strongs_lemma']}): {reason}")
        if verdict == "reject":
            rejected += 1
            if not args.dry_run:
                with con:
                    con.execute(
                        "UPDATE entries SET strongs=NULL, lemma_translit=NULL WHERE id=?",
                        (it["entry_id"],),
                    )
                    con.execute(
                        "DELETE FROM disagreements WHERE entry_id=? AND resolution_by='auto:strongs-snap'",
                        (it["entry_id"],),
                    )
                    con.execute(
                        """INSERT INTO disagreements
                           (entry_id, field, producer_value, reviewer_value,
                            resolution, resolution_by, resolved_at)
                           VALUES (?,?,?,?,?,?,?)""",
                        (it["entry_id"], "strongs",
                         f"{it['snapped_strongs']} (auto-snap to {it['strongs_lemma']}, Codex REJECT)",
                         "G_N/A",
                         f"Codex snap-audit reject: {reason}",
                         "manual:strongs-fix", now),
                    )
        elif verdict == "keep":
            kept += 1

    con.close()
    print(f"\nkept: {kept}  rejected: {rejected}  ({'dry-run, no writes' if args.dry_run else 'applied'})")
    if rejected and not args.dry_run:
        print("Rejected snaps reverted to NULL and tombstoned (manual:strongs-fix) so phase3 won't re-snap them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
