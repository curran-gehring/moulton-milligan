"""Phase 3 homograph disambiguation (Codex cross-family).

phase3_strongs.py keys a lemma by EXACT match and, on a collision (one Greek
spelling -> multiple Strong's numbers), keeps the LOWEST-numbered id. That
silently mis-keys homographs: e.g. ἄπειμι is BOTH G0548 ("be absent", from εἰμί)
and G0549 ("go away", from εἶμι); βάτος is G0942 (bush) and G0943 (dry-measure).

This pass finds every keyed entry whose normalized lemma maps to >1 Strong's id
in the index, and asks Codex (a different model family than the producer) to pick
the correct id for THAT entry from its body + NT references. Mismatches are
corrected; every decision is logged as a `manual:strongs-fix` disagreement so the
pass is idempotent (settled entries are skipped on re-run) and phase3's re-snap
guard sees real keys (reviewer_value != 'G_N/A' so it never tombstones).

Run after each phase3 wave (or once before final export). Idempotent.

Usage:
  python scripts/phase3_disambiguate_homographs.py --dry-run
  python scripts/phase3_disambiguate_homographs.py
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from codex_call import codex_exec  # noqa: E402

DB_PATH = ROOT / "state" / "run.sqlite"
INDEX_PATH = ROOT / "reference" / "strongs_lemma_index.json"

JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").strip()
    while s.endswith("."):
        s = s[:-1].strip()
    return s


# Classic Strong's Greek numbers run 1..5624; STEPBible adds EXTENDED numbers
# above that for critical-text spellings / extra lexemes. NT text (openscriptures,
# MorphGNT, STEPBible TBESG) is tagged with the CLASSIC number, so an extended key
# would orphan the entry from the NT. Prefer classic whenever one exists.
CLASSIC_MAX = 5624


def strongs_num(sid: str) -> int:
    m = re.search(r"(\d+)", sid or "")
    return int(m.group(1)) if m else 0


def prefer_classic(cands: list[str]) -> list[str]:
    classic = [c for c in cands if strongs_num(c) <= CLASSIC_MAX]
    return classic if classic else cands


def extract_json_array(text: str):
    if not text:
        return None
    cands = []
    m = JSON_FENCE.search(text)
    if m:
        cands.append(m.group(1))
    cands.append(text)
    i = text.find("[")
    if i >= 0:
        cands.append(text[i:])
    for c in cands:
        try:
            v = json.loads(c)
            if isinstance(v, list):
                return v
        except json.JSONDecodeError:
            continue
    return None


PROMPT_HEAD = """You are the adversarial Strong's-key auditor for the Moulton-Milligan lexicon.

Each item below is a lexicon entry whose Greek headword is a HOMOGRAPH: the exact
spelling maps to MORE THAN ONE Strong's number (different lexemes that happen to
share spelling). A naive keyer defaulted each to one candidate; some are wrong.

For each item, choose the Strong's id from `candidates` that matches the lexeme
the entry actually describes, judging from `body_excerpt` and `nt_references`.
You know what each Strong's number denotes. Example: ἄπειμι G0548 = "be absent"
(from εἰμί) vs G0549 = "go away" (from εἶμι); βάτος G0942 = bramble/bush vs
G0943 = Hebrew liquid measure. If the entry clearly covers BOTH senses, pick the
one its NT references / primary discussion emphasize.

Return ONLY a JSON array, no prose:
[{"idx": <int>, "chosen_strongs": "G####", "confidence": 0.0-1.0, "reason": "<=160 chars"}]
chosen_strongs MUST be one of that item's candidates.

ITEMS:
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout", type=int, default=420)
    args = ap.parse_args()

    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    form_to_ids: dict[str, set] = defaultdict(set)
    for sid, e in idx.items():
        forms = set(e.get("variants") or [])
        forms.add(e.get("lemma") or "")
        for f in forms:
            fn = norm(f)
            if fn:
                form_to_ids[fn].add(sid)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, page_no, lemma_greek, strongs, body_markdown, nt_references "
        "FROM entries WHERE strongs IS NOT NULL ORDER BY page_no, position_on_page"
    ).fetchall()

    now = datetime.now(timezone.utc).isoformat()
    auto_fixed = 0  # deterministic classic-over-extended resolutions (no Codex needed)
    items = []
    for r in rows:
        cand_all = sorted(form_to_ids.get(norm(r["lemma_greek"]), set()))
        if len(cand_all) < 2:
            continue
        # Skip entries already adjudicated by a manual strongs decision (idempotency).
        settled = con.execute(
            "SELECT 1 FROM disagreements WHERE entry_id=? AND resolution_by='manual:strongs-fix' "
            "AND field='strongs' LIMIT 1",
            (r["id"],),
        ).fetchone()
        if settled:
            continue
        # Deterministic guardrail: drop extended (>5624) candidates when a classic
        # one exists. If that collapses to a single candidate, resolve it here
        # WITHOUT Codex — it's an interop rule, not a semantic judgment.
        cand = prefer_classic(cand_all)
        if len(cand) == 1:
            chosen = cand[0]
            if chosen != r["strongs"]:
                translit = idx.get(chosen, {}).get("translit")
                print(f"  [AUTO ] p{r['page_no']} {r['lemma_greek']}: {r['strongs']} -> {chosen} "
                      f"(classic-over-extended; dropped {sorted(set(cand_all)-set(cand))})")
                if not args.dry_run:
                    with con:
                        con.execute("UPDATE entries SET strongs=?, lemma_translit=? WHERE id=?",
                                    (chosen, translit, r["id"]))
                        con.execute(
                            "INSERT INTO disagreements (entry_id,field,producer_value,reviewer_value,"
                            "resolution,resolution_by,resolved_at) VALUES (?,?,?,?,?,?,?)",
                            (r["id"], "strongs", f"{r['strongs']} (homograph default)",
                             f"{chosen} (classic Strong's)",
                             f"auto: prefer classic NT Strong's over extended {sorted(set(cand_all)-set(cand))}",
                             "manual:strongs-fix", now))
                auto_fixed += 1
            else:
                # current already the classic one — record so we don't re-check each run
                print(f"  [AUTO ] p{r['page_no']} {r['lemma_greek']}: {chosen} confirmed "
                      f"(classic over extended {sorted(set(cand_all)-set(cand))})")
                if not args.dry_run:
                    with con:
                        con.execute(
                            "INSERT INTO disagreements (entry_id,field,producer_value,reviewer_value,"
                            "resolution,resolution_by,resolved_at) VALUES (?,?,?,?,?,?,?)",
                            (r["id"], "strongs", f"{r['strongs']}",
                             f"{chosen} (classic Strong's, confirmed)",
                             f"auto: classic NT Strong's confirmed over extended {sorted(set(cand_all)-set(cand))}",
                             "manual:strongs-fix", now))
            continue
        items.append({
            "idx": len(items),
            "entry_id": r["id"],
            "page_no": r["page_no"],
            "lemma": r["lemma_greek"],
            "current": r["strongs"],
            "candidates": cand,
            "cand_lemmas": {sid: idx.get(sid, {}).get("lemma") for sid in cand},
            "nt_references": json.loads(r["nt_references"] or "[]"),
            "body_excerpt": (r["body_markdown"] or "")[:280],
        })

    if not items:
        print("no unsettled homograph entries to disambiguate")
        return 0

    payload = [
        {k: it[k] for k in ("idx", "lemma", "candidates", "cand_lemmas",
                            "nt_references", "body_excerpt")}
        for it in items
    ]
    prompt = PROMPT_HEAD + json.dumps(payload, ensure_ascii=False, indent=2)
    print(f"disambiguating {len(items)} homograph entr(y/ies) via Codex...")
    raw = codex_exec(prompt, timeout=args.timeout)
    verdicts = extract_json_array(raw or "")
    if not verdicts:
        print("ERROR: could not parse Codex verdicts. Raw head:")
        print((raw or "")[:500])
        return 1

    by_idx = {v.get("idx"): v for v in verdicts if isinstance(v, dict)}
    now = datetime.now(timezone.utc).isoformat()
    changed = confirmed = 0

    for it in items:
        v = by_idx.get(it["idx"])
        if not v:
            print(f"  p{it['page_no']} {it['lemma']}: NO VERDICT (skip)")
            continue
        chosen = v.get("chosen_strongs")
        reason = (v.get("reason") or "")[:160]
        if chosen not in it["candidates"]:
            print(f"  p{it['page_no']} {it['lemma']}: invalid choice {chosen!r} (skip)")
            continue
        if chosen == it["current"]:
            tag = "OK   "
            confirmed += 1
        else:
            tag = "FIX  "
            changed += 1
        print(f"  [{tag}] p{it['page_no']} {it['lemma']}: {it['current']} -> {chosen} "
              f"({it['cand_lemmas'].get(chosen)}): {reason}")
        if args.dry_run:
            continue
        translit = idx.get(chosen, {}).get("translit")
        with con:
            if chosen != it["current"]:
                con.execute(
                    "UPDATE entries SET strongs=?, lemma_translit=? WHERE id=?",
                    (chosen, translit, it["entry_id"]),
                )
            con.execute(
                """INSERT INTO disagreements
                   (entry_id, field, producer_value, reviewer_value,
                    resolution, resolution_by, resolved_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (it["entry_id"], "strongs",
                 f"{it['current']} (homograph default)",
                 f"{chosen} {it['cand_lemmas'].get(chosen)}",
                 f"Codex homograph disambiguation: {reason}",
                 "manual:strongs-fix", now),
            )

    con.close()
    print(f"\nfixed: {changed}  confirmed: {confirmed}  ({'dry-run' if args.dry_run else 'applied'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
