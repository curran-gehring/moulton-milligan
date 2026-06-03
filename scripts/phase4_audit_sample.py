"""Phase 4c: Codex audits a 5% random sample of citation normalizations (spec).

Samples 5% (seed=42, deterministic) of all matched/expanded normalizations,
chunks them, and asks Codex (cross-family reviewer) to flag implausible ones —
especially anaphora expansions where the inherited series/volume could be wrong
(each expanded row carries the preceding citation that supplied the series).

Output: out/phase4_audit_sample.json with Codex's flagged rows.
"""
from __future__ import annotations

import json
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from codex_call import codex_exec  # noqa: E402

DB = ROOT / "state" / "run.sqlite"
OUT = ROOT / "out" / "phase4_audit_sample.json"

PROMPT_HEAD = """You are Citation-Normalization-Audit for a digitization of Moulton-Milligan's
Vocabulary of the Greek Testament (1929). Each row below shows a papyrological
citation normalization: the RAW citation as printed, and the NORM produced by
matching its series abbreviation against MM's own front-matter abbreviation
table (and, for status=expanded, by replacing a leading ib./id. anaphor with
the series+volume inherited from the PREV citation in the same entry).

Flag a row ONLY if the normalization is clearly WRONG:
 - an expanded row inherited the wrong series/volume given its PREV citation,
 - or the norm changed the citation's meaning (not mere italics/whitespace).
Do NOT flag mere formatting differences, superscripts, or untouched text.

Reply with ONLY a JSON array (no markdown fences) of objects:
[{"idx": <row idx>, "reason": "<short>"}]
Reply [] if nothing is wrong.

ROWS:
"""


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, papyri_citations_norm FROM entries WHERE papyri_citations_norm IS NOT NULL "
        "ORDER BY id").fetchall()

    sample = []
    idx = 0
    for r in rows:
        arr = json.loads(r["papyri_citations_norm"])
        for i, c in enumerate(arr):
            if c["status"] in ("matched", "expanded"):
                prev = arr[i - 1]["raw"] if (c["status"] == "expanded" and i > 0) else ""
                sample.append({"idx": idx, "entry_id": r["id"], "status": c["status"],
                               "prev": prev, "raw": c["raw"], "norm": c["norm"]})
            idx += 1

    rng = random.Random(42)
    k = max(1, int(len(sample) * 0.05))
    picked = rng.sample(sample, k)
    print(f"population {len(sample)}, sampled {len(picked)} (5%)")

    flagged = []
    CHUNK = 200
    for ci in range(0, len(picked), CHUNK):
        chunk = picked[ci:ci + CHUNK]
        lines = []
        for c in chunk:
            if c["status"] == "expanded":
                lines.append(f"#{c['idx']} [expanded] PREV: {c['prev']} | RAW: {c['raw']} | NORM: {c['norm']}")
            else:
                lines.append(f"#{c['idx']} [matched] RAW: {c['raw']} | NORM: {c['norm']}")
        prompt = PROMPT_HEAD + "\n".join(lines)
        try:
            out = codex_exec(prompt, timeout=600) or ""
            # take the last JSON array in the output
            start = out.rfind("[")
            end = out.rfind("]")
            verdicts = json.loads(out[start:end + 1]) if start != -1 and end > start else []
            if isinstance(verdicts, list):
                flagged.extend(v for v in verdicts if isinstance(v, dict))
            print(f"  chunk {ci//CHUNK + 1}: {len(chunk)} rows -> {len(verdicts)} flagged")
        except Exception as e:
            print(f"  chunk {ci//CHUNK + 1}: ERROR {e}")

    # attach context to flags
    by_idx = {c["idx"]: c for c in picked}
    detail = [{**by_idx.get(f.get("idx"), {}), "reason": f.get("reason", "")}
              for f in flagged if f.get("idx") in by_idx]
    OUT.write_text(json.dumps({"sampled": len(picked), "flagged": detail},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"TOTAL flagged: {len(detail)} / {len(picked)} sampled "
          f"({100*len(detail)/max(len(picked),1):.2f}%)")
    for d in detail[:20]:
        print(f"  entry {d.get('entry_id')} [{d.get('status')}] {d.get('raw','')[:50]} -> "
              f"{d.get('norm','')[:50]} :: {d.get('reason','')[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
