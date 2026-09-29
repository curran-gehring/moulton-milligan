"""Whole-book scan audit with Space Bunny Alpha (OpenRouter stealth model).

User-approved exception (2026-09-29) to the README's "no API keys" and
known-family review constraints. Calls go through the ARL OpenRouter proxy
(OPENROUTER_API_KEY / ARL_OPENROUTER_BASE_URL from ~/.zshenv); the model is free.

Stages, each resumable (one JSON file per page under tmp/sb_audit/<stage>/):

  propose  page scan(s) + the page's parsed entries -> exact find/replace
           patches, lemma/Strong's corrections, deletions, missing headwords
  verify   BLIND re-read: an independent call is shown only the location and
           the current text (never the proposed fix) and transcribes what is
           printed; a fix is applied only when the two readings agree
  apply    accepted changes -> state/run.sqlite in one transaction, with the
           same exactly-one-occurrence asserts as audit_apply_fixes.py; writes
           out/sb_audit_fixes.tsv + out/sb_audit_rejected.tsv

Afterward run scripts/phase4_normalize.py then scripts/phase6_export.py.

Usage:
    python3 scripts/sb_audit.py propose [--pages 262-265] [--workers 6]
    python3 scripts/sb_audit.py verify  [--pages ...]
    python3 scripts/sb_audit.py apply   [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import unicodedata

MODEL = "stealth/space-bunny-alpha"
AGENT = "space-bunny-alpha"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "tmp", "sb_audit")
MAX_IMAGES = 5


class FixRejected(Exception):
    pass


# ---------------------------------------------------------------- pure checks

def fold(s: str) -> str:
    """Accent/case/punctuation-insensitive Greek comparison key."""
    s = unicodedata.normalize("NFD", s or "").lower()
    return "".join(ch for ch in s if ch.isalpha() and not unicodedata.combining(ch))


def norm_strongs(sid: str) -> str:
    m = re.fullmatch(r"G0*(\d+)", (sid or "").strip().upper())
    if not m:
        return sid
    return "G" + m.group(1).zfill(4)


def check_patch(body: str, old: str, new: str) -> str | None:
    if not old:
        return "empty old"
    if old == new:
        return "no-op patch"
    n = body.count(old)
    if n != 1:
        return f"expected 1 occurrence of old, found {n}"
    return None


def check_strongs(sid: str, lemma: str, index: dict) -> str | None:
    o = index.get(norm_strongs(sid))
    if o is None:
        return f"unknown Strong's id {sid}"
    keys = {fold(o.get("lemma", ""))} | {fold(v) for v in o.get("variants", [])}
    parts = {fold(p) for p in re.split(r"[,/]", lemma)} | {fold(lemma)}
    if keys.isdisjoint(parts):
        return f"lemma {lemma!r} does not match index lemma {o.get('lemma')!r} for {sid}"
    return None


def _norm_text(t: str) -> str:
    return " ".join(unicodedata.normalize("NFC", t or "").split())


_SUPERS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹ⁱᵛˣᵇᶠᵃᶜᵈᵉᵍʰʲᵏˡᵐⁿᵒᵖʳˢᵗᵘʷʸᶻ",
                        "0123456789ivxbfacdeghjklmnoprstuwyz")


def _fold_conventions(t: str) -> str:
    """Ignore house-convention differences (superscripts vs plain, spacing,
    periods/middle dots) that do not change what is printed."""
    t = unicodedata.normalize("NFC", t or "").translate(_SUPERS)
    return re.sub(r"[\s.·]", "", t)


def _is_greekish(ch: str) -> bool:
    o = ord(ch)
    return (0x0370 <= o <= 0x03FF or 0x1F00 <= o <= 0x1FFF
            or unicodedata.combining(ch) > 0 or ch in "[]<>⟨⟩")


def touches_greek(old: str, new: str) -> bool:
    """True if the edit changes Greek letters, accents/breathings or editorial
    brackets. Ground truth (2026-09-29): citation-number fixes were 22/22
    correct after blind agreement, Greek-text fixes 0/2 — so those go to
    manual review instead of being applied."""
    import difflib
    a, b = unicodedata.normalize("NFD", old), unicodedata.normalize("NFD", new)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal" and any(_is_greekish(ch) for ch in a[i1:i2] + b[j1:j2]):
            return True
    return False


def edit_sites(old: str, new: str) -> int:
    """Number of separate places a patch changes, at word level. Ground truth
    (2026-09-29): a two-site fix had one site right and one misread that the
    blind re-read repeated, so multi-site fixes go to manual review."""
    import difflib
    a, b = unicodedata.normalize("NFC", old).split(), unicodedata.normalize("NFC", new).split()
    return sum(1 for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
               if op[0] != "equal")


def blind_verdict(change: dict, reading: dict | None) -> str:
    """Compare an independent blind re-read of the scan with a proposed change.
    accept: re-read == proposed value; false_alarm: re-read == current value;
    disagree: anything else (goes to manual review, never applied)."""
    kind = change["kind"]
    if kind == "strongs":
        return "accept"  # not printed on the page; apply_fix's index guard decides
    if kind == "delete":
        present = (reading or {}).get("present")
        return {False: "manual_delete", True: "false_alarm"}.get(present, "disagree")
    printed = (reading or {}).get("printed")
    if printed is None:
        return "disagree"
    v = _blind_compare(change, printed)
    if v == "accept" and (change["kind"] == "lemma_greek" or touches_greek(change["old"], change["new"])):
        return "manual_greek"
    if v == "accept" and edit_sites(change["old"], change["new"]) > 1:
        return "manual_multi"
    return v


def _blind_compare(change: dict, printed: str) -> str:
    if _norm_text(printed) == _norm_text(change["new"]):
        return "accept"
    if _norm_text(printed) == _norm_text(change["old"]):
        return "false_alarm"
    p, n, o = (_fold_conventions(x) for x in (printed, change["new"], change["old"]))
    if n != o:
        if p == n:
            return "accept"
        if p == o:
            return "false_alarm"
    return "disagree"


def check_rekey(current: str | None, lemma: str, new: str, index: dict) -> str | None:
    """A Strong's re-key must land on an id whose index lemma matches, and may
    only replace an id that does NOT already match (else it's a homograph call
    the scan can't settle)."""
    err = check_strongs(new, lemma, index)
    if err:
        return err
    if current and norm_strongs(current) != norm_strongs(new) and check_strongs(current, lemma, index) is None:
        return f"homograph: current {current} already matches {lemma!r}; not re-keying to {new}"
    return None


def apply_fix(c: sqlite3.Connection, fix: dict, index: dict) -> None:
    """Apply one entry's accepted fix inside a savepoint; all-or-nothing."""
    i = fix["id"]
    c.execute("SAVEPOINT fix")
    try:
        row = c.execute(
            "SELECT lemma_greek, strongs, body_markdown, papyri_citations, nt_references "
            "FROM entries WHERE id=?", (i,)).fetchone()
        if row is None:
            raise FixRejected(f"id {i} missing")
        lemma, strongs, body, cites, refs = row
        if fix.get("delete"):
            c.execute("DELETE FROM reviews WHERE entry_id=?", (i,))
            c.execute("DELETE FROM disagreements WHERE entry_id=?", (i,))
            c.execute("DELETE FROM entries WHERE id=?", (i,))
            c.execute("RELEASE fix")
            return
        arrays = {"papyri_citations": json.loads(cites or "[]"),
                  "nt_references": json.loads(refs or "[]")}
        for p in fix.get("patches") or []:
            err = check_patch(body, p["old"], p["new"])
            if err:
                raise FixRejected(f"id {i}: {err}: {p['old']!r}")
            body = body.replace(p["old"], p["new"])
            for arr in arrays.values():
                for k, v in enumerate(arr):
                    if isinstance(v, str) and p["old"] in v:
                        arr[k] = v.replace(p["old"], p["new"])
        new_lemma = fix.get("lemma_greek") or lemma
        new_strongs = strongs
        translit = None
        if fix.get("strongs"):
            new_strongs = norm_strongs(fix["strongs"])
            err = check_rekey(strongs, new_lemma, new_strongs, index)
            if err:
                raise FixRejected(f"id {i}: {err}")
            translit = index[new_strongs].get("translit")
        c.execute(
            "UPDATE entries SET body_markdown=?, papyri_citations=?, nt_references=?, "
            "lemma_greek=?, strongs=?, lemma_translit=COALESCE(?, ?, lemma_translit) WHERE id=?",
            (body, json.dumps(arrays["papyri_citations"], ensure_ascii=False),
             json.dumps(arrays["nt_references"], ensure_ascii=False),
             new_lemma, new_strongs, translit, fix.get("lemma_translit"), i))
        c.execute("RELEASE fix")
    except Exception:
        c.execute("ROLLBACK TO fix")
        c.execute("RELEASE fix")
        raise


# ---------------------------------------------------------------- model calls

def proxy_env() -> tuple[str, str]:
    out = subprocess.run(
        ["zsh", "-c", "source ~/.zshenv; print -r -- $OPENROUTER_API_KEY; print -r -- $ARL_OPENROUTER_BASE_URL"],
        capture_output=True, text=True, check=True).stdout.split("\n")
    tok, base = out[0].strip(), out[1].strip()
    if not tok or not base:
        sys.exit("OPENROUTER_API_KEY / ARL_OPENROUTER_BASE_URL not set in ~/.zshenv")
    return tok, base


def tiles(path: str) -> list[tuple[str, bytes]]:
    """Full-resolution quarter tiles (column x half, with overlap). Whole pages
    get downsampled by the vision encoder and the superscript line numbers
    become unreadable (pilot: ~1 in 3 accepted fixes wrong on whole pages)."""
    from io import BytesIO
    from PIL import Image
    im = Image.open(path)
    w, h = im.size
    ox, oy = int(w * 0.04), int(h * 0.04)
    out = []
    for col, (x0, x1) in (("left column", (0, w // 2 + ox)), ("right column", (w // 2 - ox, w))):
        for half, (y0, y1) in (("top half", (0, h // 2 + oy)), ("bottom half", (h // 2 - oy, h))):
            buf = BytesIO()
            im.crop((x0, y0, x1, y1)).save(buf, "PNG")
            out.append((f"{col}, {half}", buf.getvalue()))
    return out


CALL_DEADLINE_S = 900


def _curl(cfg: str, body: bytes, url: str) -> tuple[int, str] | None:
    """POST via curl with a hard deadline. Auth goes through a -K config on a
    temp file so the token never appears in argv / ps."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".curlrc", delete=True) as kf, \
            tempfile.NamedTemporaryFile("wb", suffix=".json", delete=True) as bf:
        os.chmod(kf.name, 0o600)
        kf.write(cfg); kf.flush()
        bf.write(body); bf.flush()
        p = subprocess.run(
            ["curl", "-sS", "-K", kf.name, "--max-time", str(CALL_DEADLINE_S),
             "-H", "Content-Type: application/json", "-A", "curl/8.7.1",
             "-o", "-", "-w", "\n%{http_code}", "--data-binary", f"@{bf.name}", url],
            capture_output=True)
    if p.returncode == 28:  # operation timed out
        return None
    out = p.stdout.decode("utf-8", "replace")
    text, _, code = out.rpartition("\n")
    return int(code or 0), text


def call_model(system: str, text: str, images: list[str], tok: str, base: str) -> dict:
    content = [{"type": "text", "text": text}]
    for n, path in enumerate(images, 1):
        for label, data in tiles(path):
            content.append({"type": "text", "text": f"Image {n}, {label}:"})
            b64 = base64.b64encode(data).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        "reasoning": {"effort": "medium"},
        "response_format": {"type": "json_object"},
        "max_tokens": 16000,
    }
    body = json.dumps(payload).encode()
    delay = 10
    for attempt in range(8):
        # curl, not urllib: urllib's timeout is per socket read, and OpenRouter
        # keep-alive padding on a stalled upstream kept all six workers blocked
        # for 75+ minutes (2026-09-29). --max-time is a hard wall-clock limit.
        cfg = f'header = "Authorization: Bearer {tok}"\n'
        p = _curl(cfg, body, base + "/chat/completions")
        if p is None:
            err = f"no response within {CALL_DEADLINE_S}s"
        else:
            code, text = p
            if code == 200:
                try:
                    r = json.loads(text)
                    ch = r["choices"][0]
                    if ch.get("finish_reason") == "length":
                        raise ValueError("truncated (finish_reason=length)")
                    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", (ch["message"].get("content") or "").strip())
                    return json.loads(txt)
                except (ValueError, KeyError, IndexError) as e:
                    err = f"{type(e).__name__}: {e}"
            elif code in (429, 500, 502, 503, 504) or code == 0:
                err = f"HTTP {code}"
            else:
                raise RuntimeError(f"HTTP {code}: {text[:300]}")
        if attempt >= 5:
            raise RuntimeError(err)
        time.sleep(delay); delay = min(delay * 2, 300)
    raise RuntimeError("retries exhausted")


RULES = """You are auditing a digitization of Moulton & Milligan, *The Vocabulary of the
Greek Testament* (1929, public domain) against the printed page scans provided.

Hard rules:
- The SCANS are the only authority. Judge only what you can read in the images.
  Do not use recalled text of this book or of any other edition or derivative
  (in particular Allan Loder's VGNT) — if the scan is unreadable, leave it.
- Transcribe exactly as printed. Never translate, modernize, or normalize Greek
  or Latin; never add English glosses the page does not print.
- House conventions (keep them): italics as *...*; citation line numbers as
  Unicode superscript digits (P Oxy II. 237^viii.7 -> 237ᵛⁱⁱⁱ·⁷ style as already
  used in the entry); page-break hyphenation joined; running heads, page
  numbers and column furniture excluded.
- Each page arrives as four overlapping full-resolution tiles (left column
  top/bottom, right column top/bottom); read columns left then right. The
  overlap means a line can appear in two tiles — do not double-count it.
- Image 1 is the entry's start page. Later images are the following
  page(s), included because the last entry may continue onto them. Text at the
  top of the FIRST image before the first headword belongs to the previous
  page's entry — ignore it. Headwords that START on a later image belong to
  later pages and are audited separately — never report them as missing.
- Refer to pages by image number (image 1, image 2, ...), not the printed
  book page numbers, which differ from the scan numbering.
"""

PROPOSE_TASK = """Compare each parsed entry below against the scan(s). Report ONLY real
discrepancies: OCR misreadings (wrong Greek letters/accents/breathings, wrong
citation numbers or superscripts, wrong dates), hallucinated or dropped text,
text clipped at a page break, text belonging to a different entry, a wrong
headword, or a wrong Strong's number. Ignore purely stylistic choices.

Fixes to body_markdown must be exact find/replace patches: "old" must be a
verbatim substring of the CURRENT body that occurs exactly once (include enough
context to make it unique; keep it short), "new" is the corrected text.
To restore clipped/dropped text, anchor "old" on adjacent existing text.

Entries JSON:
{entries}

Return a JSON object:
{{"entries": [ {{"id": <int>,
   "patches": [{{"old": "...", "new": "...", "reason": "..."}}],
   "lemma_greek": <corrected headword or null>,
   "lemma_translit": <corrected transliteration or null>,
   "strongs": <corrected Strong's id like "G0697", or null>,
   "delete": <true only if this entry does not exist on the scan at all>,
   "reason": "<short summary>"}} ],
 "missing_headwords": [ {{"headword": "...", "after_id": <id of preceding entry>, "note": "..."}} ] }}
missing_headwords: only headwords that START on image 1 and are absent from the entries list.
List only entries that need a change; use [] when everything matches."""

VERIFY_TASK = """Transcription check. Each item below points at a short stretch of an
entry's parsed text ("db_text"), which may or may not contain OCR errors. Find
that exact stretch in the scan and transcribe what is ACTUALLY PRINTED for the
same extent, character for character, in the same house conventions (Unicode
superscript line numbers, *italics*). Zoom in mentally on small superscripts;
read every digit. Do not assume db_text is right or wrong.

For items with "question": "headword_present", answer whether a dictionary
entry with that headword STARTS on image 1.

Entries (for locating the text):
{entries}

Items:
{changes}

Return a JSON object:
{{"readings": [ {{"key": "<key>", "printed": "<transcription>"}}
             or {{"key": "<key>", "present": true|false}} ]}}
Include every key exactly once; if illegible use "printed": null."""


def blind_items(changes: list[dict], entries: list[dict]) -> list[dict]:
    """What the blind verifier sees: location only, never the proposed value."""
    lemma = {e["id"]: e["lemma_greek"] for e in entries}
    items = []
    for x in changes:
        if x["kind"] == "patch":
            items.append({"key": x["key"], "entry_id": x["id"], "headword": lemma.get(x["id"]),
                          "db_text": x["old"]})
        elif x["kind"] == "lemma_greek":
            items.append({"key": x["key"], "entry_id": x["id"],
                          "db_text": lemma.get(x["id"]), "what": "the entry's printed headword"})
        elif x["kind"] == "delete":
            items.append({"key": x["key"], "question": "headword_present",
                          "headword": lemma.get(x["id"])})
    return items


# ---------------------------------------------------------------- orchestration

def db(readonly=True) -> sqlite3.Connection:
    p = os.path.join(ROOT, "state", "run.sqlite")
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True) if readonly else sqlite3.connect(p)


def page_plan(c) -> dict[int, list[int]]:
    """page -> image pages: start page plus continuation pages up to and
    including the next page on which an entry starts."""
    starts = [r[0] for r in c.execute("SELECT DISTINCT page_no FROM entries ORDER BY 1")]
    plan = {}
    for k, p in enumerate(starts):
        nxt = starts[k + 1] if k + 1 < len(starts) else p + 1
        plan[p] = list(range(p, min(nxt, 735) + 1))[:MAX_IMAGES]
    return plan


def page_entries(c, page: int) -> list[dict]:
    rows = c.execute(
        "SELECT id, lemma_greek, lemma_translit, strongs, body_markdown FROM entries "
        "WHERE page_no=? ORDER BY position_on_page, id", (page,)).fetchall()
    return [dict(zip(("id", "lemma_greek", "lemma_translit", "strongs", "body_markdown"), r))
            for r in rows]


def png(p: int) -> str:
    return os.path.join(ROOT, "pages", f"page-{p:03d}.png")


def parse_pages(spec: str | None, plan: dict) -> list[int]:
    if not spec:
        return sorted(plan)
    out = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return sorted(p for p in out if p in plan)


def changes_of(proposal: dict) -> list[dict]:
    """Flatten a proposal into individually verifiable changes."""
    out = []
    for e in proposal.get("entries") or []:
        i = e.get("id")
        for k, p in enumerate(e.get("patches") or []):
            out.append({"key": f"{i}:patch:{k}", "id": i, "kind": "patch", **p})
        if e.get("lemma_greek"):
            out.append({"key": f"{i}:lemma_greek", "id": i, "kind": "lemma_greek",
                        "old": e.get("_cur_lemma", ""), "new": e["lemma_greek"], "value": e["lemma_greek"]})
        if e.get("strongs") and norm_strongs(e["strongs"]) != norm_strongs(e.get("_cur_strongs") or ""):
            out.append({"key": f"{i}:strongs", "id": i, "kind": "strongs", "value": e["strongs"]})
        if e.get("delete"):
            out.append({"key": f"{i}:delete", "id": i, "kind": "delete", "reason": e.get("reason")})
    return out


def with_current(proposal: dict, entries: list[dict]) -> dict:
    cur = {e["id"]: e for e in entries}
    for e in proposal.get("entries") or []:
        e["_cur_lemma"] = cur.get(e.get("id"), {}).get("lemma_greek", "")
        e["_cur_strongs"] = cur.get(e.get("id"), {}).get("strongs")
    return proposal


def run_stage(stage: str, pages: list[int], plan: dict, workers: int) -> None:
    tok, base = proxy_env()
    os.makedirs(os.path.join(TMP, stage), exist_ok=True)
    def work(p: int) -> str:
        out = os.path.join(TMP, stage, f"page-{p:03d}.json")
        if os.path.exists(out):
            return f"{p} cached"
        ents = page_entries(db(), p)  # sqlite connections are per-thread
        imgs = [png(q) for q in plan[p] if os.path.exists(png(q))]
        ej = json.dumps(ents, ensure_ascii=False, indent=1)
        if stage == "propose":
            res = call_model(RULES, PROPOSE_TASK.format(entries=ej), imgs, tok, base)
        else:
            src = os.path.join(TMP, "propose", f"page-{p:03d}.json")
            if not os.path.exists(src):
                return f"{p} no proposal"
            items = blind_items(changes_of(with_current(
                json.load(open(src, encoding="utf-8")), ents)), ents)
            if not items:
                res = {"readings": []}
            else:
                res = call_model(RULES, VERIFY_TASK.format(
                    entries=ej, changes=json.dumps(items, ensure_ascii=False, indent=1)),
                    imgs, tok, base)
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n = len(res.get("entries") or res.get("readings") or [])
        return f"{p} ok ({n})"

    done = 0
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(work, p): p for p in pages}
        for f in cf.as_completed(futs):
            done += 1
            try:
                msg = f.result()
            except Exception as e:  # keep going; failed pages rerun on next invocation
                msg = f"{futs[f]} FAILED {e}"
            print(f"[{done}/{len(pages)}] {stage} {msg}", flush=True)


def run_apply(dry_run: bool) -> None:
    index = json.load(open(os.path.join(ROOT, "reference", "strongs_lemma_index.json"), encoding="utf-8"))
    c = db(readonly=False)
    c.execute("BEGIN")
    applied, rejected, disagree, missing = [], [], [], []
    for fn in sorted(os.listdir(os.path.join(TMP, "propose"))):
        prop = json.load(open(os.path.join(TMP, "propose", fn), encoding="utf-8"))
        page = int(fn[5:8])
        for m in prop.get("missing_headwords") or []:
            missing.append((page, m.get("headword"), m.get("after_id"), m.get("note")))
        vpath = os.path.join(TMP, "verify", fn)
        ch = changes_of(with_current(prop, page_entries(c, page)))
        if not ch:
            continue
        if not os.path.exists(vpath):
            rejected += [(page, x["id"], x["key"], "not verified yet", json.dumps(x, ensure_ascii=False)) for x in ch]
            continue
        reading = {r.get("key"): r for r in json.load(open(vpath, encoding="utf-8")).get("readings") or []}
        by_id: dict[int, dict] = {}
        for x in ch:
            r = reading.get(x["key"])
            v = blind_verdict(x, r)
            if v == "false_alarm":
                rejected.append((page, x["id"], x["key"], "blind re-read matches current text",
                                 json.dumps(x, ensure_ascii=False)))
                continue
            if v in ("disagree", "manual_greek", "manual_delete", "manual_multi"):
                disagree.append((page, x["id"], x["key"], v, x.get("old", ""), x.get("new", ""),
                                 (r or {}).get("printed", (r or {}).get("present", "")), x.get("reason", "")))
                continue
            fix = by_id.setdefault(x["id"], {"id": x["id"], "patches": [], "_keys": []})
            fix["_keys"].append(x)
            if x["kind"] == "patch":
                fix["patches"].append({"old": x["old"], "new": x["new"]})
            elif x["kind"] == "delete":
                fix["delete"] = True
            else:
                fix[x["kind"]] = x["value"]
        for fix in by_id.values():
            try:
                apply_fix(c, fix, index)
                for x in fix["_keys"]:
                    applied.append((page, x["id"], x["key"], x.get("old") or "", x.get("new") or x.get("value") or "delete",
                                    x.get("reason") or ""))
            except FixRejected as e:
                rejected += [(page, x["id"], x["key"], f"guard: {e}", json.dumps(x, ensure_ascii=False)) for x in fix["_keys"]]
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)

    def tsv(name, header, rows):
        with open(os.path.join(ROOT, "out", name), "w", encoding="utf-8") as f:
            f.write("\t".join(header) + "\n")
            for r in rows:
                f.write("\t".join(str(v).replace("\t", " ").replace("\n", "⏎") for v in r) + "\n")

    tsv("sb_audit_fixes.tsv", ["page", "entry_id", "key", "old", "new", "reason"], applied)
    tsv("sb_audit_rejected.tsv", ["page", "entry_id", "key", "why", "change"], rejected)
    tsv("sb_audit_disagreements.tsv", ["page", "entry_id", "key", "why", "current", "proposed", "blind_reread", "reason"],
        disagree)
    tsv("sb_audit_missing_headwords.tsv", ["page", "headword", "after_id", "note"], missing)
    if dry_run:
        c.execute("ROLLBACK")
    else:
        c.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (
            "sb_audit_applied",
            f"{time.strftime('%Y-%m-%d')} {AGENT}: {len(applied)} changes applied, "
            f"{len(rejected)} rejected, {len(disagree)} disagreements for manual review, "
            f"{len(missing)} missing-headword reports (out/sb_audit_*.tsv)"))
        c.execute("COMMIT")
    print(f"{'DRY RUN — ' if dry_run else ''}applied {len(applied)}, rejected {len(rejected)}, "
          f"disagreements {len(disagree)}, missing headwords {len(missing)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["propose", "verify", "apply"])
    ap.add_argument("--pages")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.stage == "apply":
        run_apply(a.dry_run)
        return 0
    plan = page_plan(db())
    run_stage(a.stage, parse_pages(a.pages, plan), plan, a.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
