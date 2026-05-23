"""Phase 1A: Tesseract baseline OCR for every page.

For each pages/page-NNN.png:
  - run `tesseract <png> <basename> -l grc+eng --psm 4`
  - register the page in state/run.sqlite (pages table)
  - store ocr_text alongside as pages/page-NNN.txt
  - update pages.ocr_text + ocr_status='done', ocr_agent='tesseract'

Resumable: skips pages that are already ocr_status='done' for tesseract.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "run.sqlite"
PAGES_DIR = ROOT / "pages"

DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PAGE_RE = re.compile(r"^page-(\d+)\.png$")


def find_tesseract() -> str:
    env = os.environ.get("TESSERACT_BIN")
    if env and Path(env).exists():
        return env
    if Path(DEFAULT_TESSERACT).exists():
        return DEFAULT_TESSERACT
    return "tesseract"


def discover_pages() -> list[tuple[int, Path]]:
    out: list[tuple[int, Path]] = []
    for p in sorted(PAGES_DIR.glob("page-*.png")):
        m = PAGE_RE.match(p.name)
        if not m:
            continue
        out.append((int(m.group(1)), p))
    return out


def register_pages(con: sqlite3.Connection, pages: list[tuple[int, Path]]) -> None:
    con.executemany(
        """
        INSERT OR IGNORE INTO pages (page_no, png_path)
        VALUES (?, ?)
        """,
        [(no, str(path)) for no, path in pages],
    )
    con.commit()


def pending_pages(con: sqlite3.Connection) -> list[tuple[int, str]]:
    rows = con.execute(
        """
        SELECT page_no, png_path
          FROM pages
         WHERE ocr_status != 'done' OR ocr_agent != 'tesseract' OR ocr_text IS NULL
         ORDER BY page_no
        """
    ).fetchall()
    return rows


def run_tesseract(tess_bin: str, png: Path) -> tuple[bool, str]:
    txt_base = png.with_suffix("")  # tesseract appends .txt
    cmd = [tess_bin, str(png), str(txt_base), "-l", "grc+eng", "--psm", "4"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return False, ""
    if proc.returncode != 0:
        return False, proc.stderr
    txt_file = txt_base.with_suffix(".txt")
    if not txt_file.exists():
        return False, "no output file"
    return True, txt_file.read_text(encoding="utf-8", errors="replace")


def worker(tess_bin: str, page_no: int, png_path: str) -> tuple[int, bool, str]:
    ok, body = run_tesseract(tess_bin, Path(png_path))
    return page_no, ok, body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="cap pages per run for testing")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"Run init_state_db.py first: {DB_PATH}", file=sys.stderr)
        return 1
    if not PAGES_DIR.exists():
        print(f"No pages dir: {PAGES_DIR}", file=sys.stderr)
        return 1

    tess_bin = find_tesseract()
    print(f"tesseract: {tess_bin}")

    con = sqlite3.connect(DB_PATH)
    try:
        pages = discover_pages()
        print(f"discovered {len(pages)} PNGs")
        register_pages(con, pages)
        pending = pending_pages(con)
        if args.limit is not None:
            pending = pending[: args.limit]
        print(f"pending: {len(pending)}")

        done = 0
        failed = 0
        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(worker, tess_bin, no, path) for no, path in pending]
            for fut in as_completed(futures):
                page_no, ok, body = fut.result()
                ts = datetime.now(timezone.utc).isoformat()
                if ok:
                    con.execute(
                        "UPDATE pages SET ocr_text=?, ocr_status='done', ocr_agent='tesseract', ocr_at=? WHERE page_no=?",
                        (body, ts, page_no),
                    )
                    done += 1
                else:
                    con.execute(
                        "UPDATE pages SET ocr_status='failed', ocr_agent='tesseract', ocr_at=? WHERE page_no=?",
                        (ts, page_no),
                    )
                    failed += 1
                if (done + failed) % 25 == 0:
                    con.commit()
                    elapsed = time.monotonic() - start
                    rate = (done + failed) / elapsed if elapsed > 0 else 0
                    print(f"  done={done} failed={failed} rate={rate:.1f} pages/s")
        con.commit()
        elapsed = time.monotonic() - start
        print(f"complete: done={done} failed={failed} elapsed={elapsed:.1f}s")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
