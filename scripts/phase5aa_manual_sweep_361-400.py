"""Phase 5aa: residual disagreement sweep for the 361-400 batch (waves AG-AJ).

Auto-resolver (phase5_resolve) closed 48 of 96. This handles the remaining 46:

MERGE (12) — continuation fragments are the tail of the prior page's truncated
entry (verified: e.g. p361 καταριθμέω "...ὑποτε-" + p362 frag "λεῖς..."). The
parser labeled each with the running-header LEFT lemma (rule 7), colliding with
the real same-named entry on the page. Append fragment body to the prior-page
head, delete the fragment (+ its disagreements/reviews). The real same-named
entry (e.g. the actual καταρτίζω) is a separate row and is untouched.

p395 κύριος/κυριεύω SPLIT (d#846/847/849/850) — the single p395 entry begins
with the κυριεύω tail (p394 ended "...τῶν προγό-" + "νων μου κεκυριευκότων...")
then the κύριος article. Move the κυριεύω-tail prefix (text before "## κύριος"
in the vision md) onto p394 κυριεύω (id 2791); κύριος (id 2792) keeps the rest.
Reassign NT refs: Rom 6⁹/6¹⁴ are κυριεύω ("death/sin no longer κυριεύει");
2 Cor 3¹⁷ + Mk 13³⁵ + 1 Cor 10²¹ + Lk 2¹¹ + Col 3¹⁷ stay κύριος. (d#844/845
keep-producer: κυριεύω is Lk 22²⁵ — reviewer's 22⁵² is a transposition.)

ADOPT-REVIEWER NT adds (4) — real NT attestations the producer left in body:
  d#785 κέραμος += Lk 5¹⁹ ; d#788 κεράτιον += Lk 15¹⁶ ;
  d#810 κοιτών += Ac 12²⁰ ; d#817 κολοβόω += Mk 13²⁰
ADOPT-REVIEWER NT book-prefix (1) — d#833 κρίνω: add Ac prefix to chained refs.

KEEP-PRODUCER (rest) — soft-hyphen line-break artifacts (p391), citation
anaphora / edition cross-refs / witness sigla, identical-after-normalization.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"
VISION = ROOT / "pages" / "page-395.vision.md"


def smart_join(head_body: str, frag_body: str) -> str:
    h = head_body.rstrip()
    f = frag_body.lstrip()
    if h.endswith("-"):
        return h[:-1] + f          # rejoin a hyphenated line-break word
    return h + " " + f


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    merged = adopted = kept = split = 0

    with con:
        # ---------- 1. p395 κύριος / κυριεύω split ----------
        md = VISION.read_text(encoding="utf-8")
        lines = md.split("\n")
        pre, post, seen = [], [], False
        for ln in lines[1:]:                     # skip running header line
            if ln.startswith("## κύριος"):
                seen = True
                continue
            (post if seen else pre).append(ln)
        pre_txt = "\n".join(pre).strip()
        post_txt = "\n".join(post).strip()
        if pre_txt and post_txt:
            k = con.execute("SELECT body_markdown FROM entries WHERE id=2791").fetchone()
            con.execute("UPDATE entries SET body_markdown=? WHERE id=2791",
                        (smart_join(k["body_markdown"], pre_txt),))
            con.execute("UPDATE entries SET body_markdown=? WHERE id=2792", (post_txt,))
            con.execute("UPDATE entries SET nt_references=? WHERE id=2791",
                        (json.dumps(["Lk 22²⁵", "Rom 6⁹", "Rom 6¹⁴"], ensure_ascii=False),))
            con.execute("UPDATE entries SET nt_references=? WHERE id=2792",
                        (json.dumps(["2 Cor 3¹⁷", "Mk 13³⁵", "1 Cor 10²¹", "Lk 2¹¹", "Col 3¹⁷"],
                                    ensure_ascii=False),))
            for did in (846, 847, 849, 850):
                con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                               WHERE id=? AND resolution IS NULL""",
                            ("split κυριεύω tail off into p394 κυριεύω; κύριος keeps the article body; "
                             "Rom 6⁹/6¹⁴ -> κυριεύω, rest stay κύριος", "manual:split", now, did))
                split += 1

        # ---------- 2. continuation-fragment merges ----------
        merges = [
            (2509, 2508), (2519, 2518), (2564, 2563), (2575, 2574),
            (2584, 2583), (2594, 2593), (2624, 2623), (2634, 2633),
            (2658, 2657), (2676, 2675), (2695, 2694), (2723, 2722),
        ]
        for frag_id, head_id in merges:
            fr = con.execute("SELECT body_markdown FROM entries WHERE id=?", (frag_id,)).fetchone()
            hd = con.execute("SELECT body_markdown FROM entries WHERE id=?", (head_id,)).fetchone()
            if not fr or not hd:
                continue
            con.execute("UPDATE entries SET body_markdown=? WHERE id=?",
                        (smart_join(hd["body_markdown"], fr["body_markdown"]), head_id))
            con.execute("DELETE FROM disagreements WHERE entry_id=?", (frag_id,))
            con.execute("DELETE FROM reviews WHERE entry_id=?", (frag_id,))
            con.execute("DELETE FROM entries WHERE id=?", (frag_id,))
            merged += 1

        # ---------- 3. adopt-reviewer NT adds ----------
        nt_adds = {
            785: (2600, ["Lk 5¹⁹"]),
            788: (2603, ["Lk 15¹⁶"]),
            810: (2687, ["Ac 12²⁰"]),
            817: (2698, ["Mk 13²⁰"]),
            833: (2752, ["Ac 20¹⁶", "1 Cor 2²", "Tit 3¹²", "Jn 19²²", "Lk 12⁵⁷",
                         "1 Cor 6²", "Ac 15¹⁹", "Ac 13⁴⁸", "Ac 16¹⁵", "Ac 26⁸"]),
        }
        for did, (eid, nt) in nt_adds.items():
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("UPDATE entries SET nt_references=? WHERE id=?",
                        (json.dumps(nt, ensure_ascii=False), eid))
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("adopt reviewer: real NT attestation(s) the producer left in body / book-prefix fix",
                         "manual:adopt-reviewer", now, did))
            adopted += 1

        # ---------- 4. keep-producer (benign residue) ----------
        keep = [758, 772, 773, 791, 798, 800, 801, 804, 807, 809, 815, 820,
                834, 835, 836, 837, 838, 839, 840, 841, 842, 844, 845, 855, 856]
        for did in keep:
            r = con.execute("SELECT resolution FROM disagreements WHERE id=?", (did,)).fetchone()
            if not r or r["resolution"] is not None:
                continue
            con.execute("""UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                           WHERE id=? AND resolution IS NULL""",
                        ("benign: soft-hyphen line-break / citation anaphora / witness siglum / "
                         "edition cross-ref / correct-as-producer (e.g. κυριεύω Lk 22²⁵); "
                         "Phase 4 normalizes citations", "manual:keep-producer", now, did))
            kept += 1

    print(f"split: {split}  merged: {merged}  adopted: {adopted}  kept: {kept}")
    rem = con.execute("""SELECT COUNT(*) FROM disagreements d JOIN entries e ON e.id=d.entry_id
                         WHERE e.page_no BETWEEN 361 AND 400 AND d.resolution IS NULL""").fetchone()[0]
    print(f"open disagreements 361-400 remaining: {rem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
