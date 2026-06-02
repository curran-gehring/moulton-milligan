"""One-off: ingest Claude-agent adversarial verdicts for pages 516-518 into the
reviews + disagreements tables, mirroring phase2_audit.audit_page's DB writes.

Used because the local Codex ChatGPT OAuth grant died mid-audit ('invalid_grant:
Grant not found') and these 3 pages couldn't be Codex-audited. A fresh Claude
agent re-derived each entry from the page markdown (independent perspective, zero
context on the parse). Reviewer tagged 'claude-review' to distinguish from 'codex'.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"
REVIEW = ROOT / "tmp" / "review"


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    total = {"agree": 0, "minor": 0, "major": 0, "reject": 0}

    for pno in (516, 517, 518):
        payload = json.loads((REVIEW / f"verdict-{pno}.json").read_text(encoding="utf-8"))
        entries = con.execute(
            "SELECT id, position_on_page FROM entries WHERE page_no=? ORDER BY position_on_page",
            (pno,),
        ).fetchall()
        pos2id = {r["position_on_page"]: r["id"] for r in entries}
        ids = list(pos2id.values())
        ph = ",".join("?" for _ in ids)
        with con:
            con.execute(f"DELETE FROM disagreements WHERE entry_id IN ({ph})", ids)
            con.execute(
                f"DELETE FROM reviews WHERE entry_id IN ({ph}) AND reviewer_agent IN ('codex','claude-review')",
                ids,
            )
            for v in payload["verdicts"]:
                pos = v.get("parser_position")
                verdict = (v.get("verdict") or "").lower()
                if verdict not in total:
                    verdict = "agree"
                total[verdict] += 1
                eid = pos2id.get(pos)
                if not eid:
                    continue
                fd = v.get("field_diffs") or {}
                con.execute(
                    """INSERT INTO reviews (entry_id, reviewer_agent, verdict, diff,
                         reviewer_lemma, reviewer_strongs, notes, reviewed_at)
                       VALUES (?, 'claude-review', ?, ?, ?, NULL, ?, ?)""",
                    (eid, verdict, json.dumps(fd, ensure_ascii=False),
                     v.get("reviewer_lemma"), v.get("notes") or "", now),
                )
                if verdict in ("minor", "major", "reject"):
                    for field, vals in fd.items():
                        prod = (vals or {}).get("producer")
                        rev = (vals or {}).get("reviewer")
                        if not isinstance(prod, (str, type(None))):
                            prod = json.dumps(prod, ensure_ascii=False)
                        if not isinstance(rev, (str, type(None))):
                            rev = json.dumps(rev, ensure_ascii=False)
                        con.execute(
                            """INSERT INTO disagreements (entry_id, field, producer_value,
                                 reviewer_value, resolution, resolution_by, resolved_at)
                               VALUES (?, ?, ?, ?, NULL, NULL, NULL)""",
                            (eid, field, prod, rev),
                        )
        print(f"page {pno}: ingested {len(payload['verdicts'])} verdicts")

    print(f"totals: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
