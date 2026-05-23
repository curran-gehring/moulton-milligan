"""Subprocess wrapper around `codex exec` (per spec §3.2).

Used by Phase 2 (entry parsing audit), Phase 3 (Strong's snap audit),
and Phase 4 (citation normalization audit) — anywhere we need the
adversarial reviewer to be a different model family than the producer.

Returns the final agent_message text (the JSON streamed via --json is
consumed and the last `item.completed` agent_message is extracted).
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Optional


def codex_exec(prompt: str, *, model: Optional[str] = None, timeout: int = 180) -> Optional[str]:
    """Run `codex exec` with a stdin-piped prompt; return last agent message text.

    On error or non-zero exit, returns None and prints stderr.
    """
    # Resolve the actual binary (Windows: codex is a .cmd shim)
    import shutil
    codex_bin = shutil.which("codex.cmd") or shutil.which("codex")
    if not codex_bin:
        print("codex_exec: codex CLI not found on PATH", file=sys.stderr)
        return None
    cmd = [codex_bin, "exec", "--skip-git-repo-check", "--json"]
    if model:
        cmd += ["--model", model]
    cmd += ["-"]
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"codex_exec: timeout after {timeout}s", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(f"codex_exec: non-zero exit {proc.returncode}\n{proc.stderr}", file=sys.stderr)
        return None
    last_msg = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") == "item.completed":
            item = evt.get("item", {})
            if item.get("type") == "agent_message":
                last_msg = item.get("text")
    return last_msg


if __name__ == "__main__":
    test_prompt = "Reply with the single word OK and nothing else."
    out = codex_exec(test_prompt, timeout=60)
    print(f"smoke test result: {out!r}")
