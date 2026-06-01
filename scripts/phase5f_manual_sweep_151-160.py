"""Phase 5f: one-shot manual sweep of residual disagreements for wave L.

Encodes per-case decisions for the disagreements left open by phase5_resolve.py
across pages 151-160 (the Γ section, parsed 2026-06-01). Mirrors phase5b/c/d/e.

Four residuals:
  - 2 papyri_citations_raw -> keep_producer (raw-as-written; Phase 4 normalizes):
      d#251 γεώργιον: producer also captured the embedded "P Petr III. p. 23"
        (a Mahaffy translator attribution inside the P Par 63 discussion). It is
        a citation string as-written; Phase 4 decides attestation-vs-attribution.
      d#252 γῆ: producer split "P Thead 54⁹" / "55⁹" into raw chained elements;
        reviewer merged to "P Thead 54⁹ and 55⁹". Both are faithful raw forms;
        Phase 4 normalizes chained refs.
  - 2 nt_references_raw -> ADD the reviewer's ref (attested in the body, the
    parser missed it). These are genuine content fixes, the kind Phase 5 owns:
      d#254 γίνομαι (p156): body reads "...so common in NT, esp. in Ac, as ⁹·³
        ἐὰν γένηταί με ἀποδημεῖν" -> Ac 9³ is a real NT reference. Insert it
        after "Gal 4⁴" (the reviewer's position).
      d#256 γλῶσσα (p158): body reads "...as in Ac 2⁴ (cf. ⁶)" -> the chained
        "(cf. ⁶)" = Ac 2⁶. Append it.

Kinds: "keep_producer", "add_nt_ref".
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"

# did -> (kind, *args)
#   keep_producer: (note,)
#   add_nt_ref:    (ref_to_add, insert_index_or_None, note)  None index = append
DECISIONS: dict[int, tuple] = {
    251: ("keep_producer",
          "embedded 'P Petr III. p. 23' is a Mahaffy translator attribution; raw-as-written, Phase 4"),
    252: ("keep_producer",
          "'P Thead 54⁹'/'55⁹' split vs reviewer 'and 55⁹' merge; both faithful raw, Phase 4 normalizes"),
    254: ("add_nt_ref", "Ac 9³", 2,
          "body: 'so common in NT, esp. in Ac, as ⁹·³ ἐὰν γένηταί...' = Acts 9:3, attested"),
    256: ("add_nt_ref", "Ac 2⁶", None,
          "body: 'as in Ac 2⁴ (cf. ⁶)' = chained Acts 2:6, attested"),
}


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    nt_added = 0
    skipped_already_resolved = 0

    with con:
        for did, decision in DECISIONS.items():
            row = con.execute(
                "SELECT entry_id, resolution FROM disagreements WHERE id=?", (did,)
            ).fetchone()
            if not row:
                print(f"  d#{did}: not found, skip")
                continue
            if row["resolution"] is not None:
                skipped_already_resolved += 1
                continue

            kind = decision[0]
            if kind == "keep_producer":
                resolution, resolution_by = decision[1], "manual:keep-producer"
            elif kind == "add_nt_ref":
                ref, idx, note = decision[1], decision[2], decision[3]
                erow = con.execute(
                    "SELECT nt_references FROM entries WHERE id=?", (row["entry_id"],)
                ).fetchone()
                refs = json.loads(erow["nt_references"] or "[]")
                if ref not in refs:
                    if idx is None or idx >= len(refs):
                        refs.append(ref)
                    else:
                        refs.insert(idx, ref)
                    con.execute(
                        "UPDATE entries SET nt_references=? WHERE id=?",
                        (json.dumps(refs, ensure_ascii=False), row["entry_id"]),
                    )
                    nt_added += 1
                resolution, resolution_by = note, "manual:accept-reviewer"
            else:
                print(f"  d#{did}: unknown kind {kind!r}; skip")
                continue

            con.execute(
                "UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=? "
                "WHERE id=? AND resolution IS NULL",
                (resolution, resolution_by, now, did),
            )
            applied += 1

    print(f"\napplied (disagreements): {applied}")
    print(f"nt_references added:     {nt_added}")
    print(f"skipped already-resolved: {skipped_already_resolved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
