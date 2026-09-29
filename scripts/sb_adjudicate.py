"""Resolve the Space Bunny audit's manual-review queue with a third reading.

Input: out/sb_audit_disagreements.tsv (from sb_audit.py apply). Each item has
the current text, Space Bunny's proposal and its independent blind re-read.

  resolve  drop stale items (text already changed by an applied fix), settle
           convention-only disagreements mechanically (sb_audit.pre_resolve),
           then ask Claude Sonnet (subscription `claude -p --model sonnet`) for
           a BLIND reading of each remaining item, one call per page, cached
           under tmp/sb_audit/sonnet/.
  apply    two-of-three agreement (sb_audit.adjudicate) -> state/run.sqlite in
           one transaction; writes out/sb_adjudicated.tsv and
           out/sb_manual_final.tsv (what is still unresolved).

Deletes are never handled here: the flagged "spurious" entries were real
continuation fragments that need merging.

Usage:
    python3 scripts/sb_adjudicate.py resolve [--pages 352] [--workers 4]
    python3 scripts/sb_adjudicate.py apply [--dry-run]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sb_audit as sb  # noqa: E402

QUEUE = os.path.join(sb.ROOT, "out", "sb_audit_disagreements.tsv")
OUT = os.path.join(sb.TMP, "sonnet")
TILES = os.path.join(sb.TMP, "tiles")
CALL_DEADLINE_S = 1800

PROMPT = """Context: this is data QA for FirstWord, a Bible-study app. The text is the
public-domain 1929 Greek lexicon Moulton & Milligan, *The Vocabulary of the Greek
Testament*, OCR'd into a database. Nothing sensitive.

Task: a blind transcription check. Each item points at a short stretch of an
entry's parsed text ("db_text") that may or may not contain OCR errors. Find that
stretch on the page scan and transcribe what is ACTUALLY PRINTED for the same
extent, character for character. Do not assume db_text is right or wrong.

Page scan tiles (full resolution, overlapping; read with the Read tool):
{tiles}
The entry starts on the first page listed; long entries continue onto later pages.

Superscript citation line numbers are tiny and 3/5/6/8 are easily confused.
For EVERY item containing a superscript or a small digit you MUST zoom before
answering (at least 4x) — never read superscripts from the unzoomed tile:
python3 -c "from PIL import Image; im=Image.open('<tile>'); im.crop((x0,y0,x1,y1)).resize(((x1-x0)*4,(y1-y0)*4), Image.LANCZOS).save('/tmp/mmadj/<name>.png')"
then Read the crop (mkdir -p /tmp/mmadj first). Greek accents, breathings and
editorial brackets must be read exactly. Never translate or normalize. Use the
house conventions of db_text (Unicode superscripts for line numbers, *italics*).

Items:
{items}

Reply with ONLY a JSON object, no prose:
{{"readings": [{{"key": "<key>", "printed": "<transcription or null if illegible>"}}]}}
Include every key exactly once."""


def load_queue() -> list[dict]:
    items = []
    for r in csv.DictReader(open(QUEUE, encoding="utf-8"), delimiter="\t"):
        kind = r["key"].split(":")[1]
        if kind == "delete":
            continue
        items.append({"key": r["key"], "page": int(r["page"]), "id": int(r["entry_id"]),
                      "kind": kind, "why": r["why"], "old": r["current"].replace("⏎", "\n"),
                      "new": r["proposed"].replace("⏎", "\n"), "reread": r["blind_reread"].replace("⏎", "\n"),
                      "reason": r["reason"]})
    return items


def is_stale(c, it: dict) -> bool:
    row = c.execute("SELECT lemma_greek, body_markdown FROM entries WHERE id=?", (it["id"],)).fetchone()
    if row is None:
        return True
    if it["kind"] == "lemma_greek":
        return sb._norm_text(row[0]) != sb._norm_text(it["old"])
    return row[1].count(it["old"]) != 1


def page_tiles(pages: list[int]) -> list[str]:
    from PIL import Image
    os.makedirs(TILES, exist_ok=True)
    out = []
    for p in pages:
        src = sb.png(p)
        if not os.path.exists(src):
            continue
        im = None
        for col, (fx0, fx1) in (("L", (0, 0.54)), ("R", (0.46, 1))):
            for row, (fy0, fy1) in (("1", (0, 0.36)), ("2", (0.31, 0.69)), ("3", (0.64, 1))):
                path = os.path.join(TILES, f"page-{p:03d}-{col}{row}.png")
                if not os.path.exists(path):
                    im = im or Image.open(src)
                    w, h = im.size
                    im.crop((int(w * fx0), int(h * fy0), int(w * fx1), int(h * fy1))).save(path)
                out.append(path)
    return out


def call_sonnet(prompt: str) -> dict:
    for attempt in range(3):
        try:
            p = subprocess.run(
                ["claude", "-p", "--model", "sonnet", "--output-format", "json",
                 "--allowedTools", "Read", "Bash(python3:*)", "Bash(mkdir:*)"],
                input=prompt, capture_output=True, text=True, cwd=sb.ROOT, timeout=CALL_DEADLINE_S,
                env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})
            res = json.loads(p.stdout)
            if res.get("is_error"):
                raise RuntimeError(str(res.get("result"))[:200])
            txt = res.get("result") or ""
            m = re.search(r"\{.*\}", txt, re.S)
            if not m:
                raise ValueError(f"no JSON in reply: {txt[:200]}")
            return json.loads(m.group(0))
        except (subprocess.TimeoutExpired, ValueError, RuntimeError, json.JSONDecodeError) as e:
            err = e
            time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"sonnet failed: {err}")


def resolve(pages_spec: str | None, workers: int) -> None:
    c = sb.db()
    plan = sb.page_plan(c)
    todo: dict[int, list[dict]] = {}
    stats = {"stale": 0, "pre_apply": 0, "pre_keep": 0, "to_sonnet": 0}
    pre = {}
    for it in load_queue():
        if is_stale(c, it):
            stats["stale"] += 1
            continue
        r = sb.pre_resolve(it)
        if r:
            pre[it["key"]] = {"decision": r[0], "text": r[1]}
            stats["pre_" + r[0]] += 1
            continue
        todo.setdefault(it["page"], []).append(it)
        stats["to_sonnet"] += 1
    os.makedirs(OUT, exist_ok=True)
    json.dump(pre, open(os.path.join(OUT, "_pre_resolved.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(stats, "pages:", len(todo), flush=True)
    pages = sorted(todo) if not pages_spec else [p for p in sb.parse_pages(pages_spec, plan) if p in todo]

    def work(p: int) -> str:
        out = os.path.join(OUT, f"page-{p:03d}.json")
        if os.path.exists(out):
            return f"{p} cached"
        ents = {e["id"]: e["lemma_greek"] for e in sb.page_entries(sb.db(), p)}
        items = [{"key": it["key"], "entry_headword": ents.get(it["id"]),
                  **({"db_text": it["old"]} if it["kind"] == "patch"
                     else {"db_text": it["old"], "what": "the entry's printed headword"})}
                 for it in todo[p]]
        tiles = page_tiles(plan.get(p, [p]))
        res = call_sonnet(PROMPT.format(tiles="\n".join(tiles),
                                        items=json.dumps(items, ensure_ascii=False, indent=1)))
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return f"{p} ok ({len(res.get('readings') or [])}/{len(items)})"

    done = 0
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(work, p): p for p in pages}
        for f in cf.as_completed(futs):
            done += 1
            try:
                msg = f.result()
            except Exception as e:
                msg = f"{futs[f]} FAILED {e}"
            print(f"[{done}/{len(pages)}] sonnet {msg}", flush=True)


def apply(dry_run: bool) -> None:
    index = json.load(open(os.path.join(sb.ROOT, "reference", "strongs_lemma_index.json"), encoding="utf-8"))
    c = sb.db(readonly=False)
    c.execute("BEGIN")
    pre = json.load(open(os.path.join(OUT, "_pre_resolved.json"), encoding="utf-8"))
    applied, residue = [], []
    for it in load_queue():
        if is_stale(c, it):
            continue
        if it["key"] in pre:
            decision, text, via = pre[it["key"]]["decision"], pre[it["key"]]["text"], "convention-only"
            reading = it["reread"]
        else:
            path = os.path.join(OUT, f"page-{it['page']:03d}.json")
            readings = {}
            if os.path.exists(path):
                readings = {r.get("key"): r.get("printed") for r in json.load(open(path, encoding="utf-8")).get("readings") or []}
            reading = readings.get(it["key"])
            decision, text = sb.adjudicate(it, reading)
            via = "sonnet"
        if decision != "apply":
            if decision == "manual":
                residue.append((it["page"], it["id"], it["key"], it["why"], it["old"], it["new"], it["reread"], reading or ""))
            continue
        fix = ({"id": it["id"], "patches": [{"old": it["old"], "new": text}]} if it["kind"] == "patch"
               else {"id": it["id"], "lemma_greek": text})
        try:
            sb.apply_fix(c, fix, index)
            applied.append((it["page"], it["id"], it["key"], via, it["old"], text))
        except sb.FixRejected as e:
            residue.append((it["page"], it["id"], it["key"], f"guard: {e}", it["old"], it["new"], it["reread"], reading or ""))

    def tsv(name, header, rows):
        with open(os.path.join(sb.ROOT, "out", name), "w", encoding="utf-8") as f:
            f.write("\t".join(header) + "\n")
            for r in rows:
                f.write("\t".join(str(v).replace("\t", " ").replace("\n", "⏎") for v in r) + "\n")

    tsv("sb_adjudicated.tsv", ["page", "entry_id", "key", "via", "old", "new"], applied)
    tsv("sb_manual_final.tsv", ["page", "entry_id", "key", "why", "current", "sb_proposed", "sb_reread", "sonnet"],
        residue)
    if dry_run:
        c.execute("ROLLBACK")
    else:
        c.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (
            "sb_adjudicate_applied",
            f"{time.strftime('%Y-%m-%d')} two-of-three with claude sonnet: {len(applied)} applied, "
            f"{len(residue)} still manual (out/sb_manual_final.tsv)"))
        c.execute("COMMIT")
    print(f"{'DRY RUN — ' if dry_run else ''}applied {len(applied)}, still manual {len(residue)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["resolve", "apply"])
    ap.add_argument("--pages")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.stage == "resolve":
        resolve(a.pages, a.workers)
    else:
        apply(a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
