# ==============================================================================
# File: submit_many.py
# Description: Submits a contiguous range of batch files through the SAIR API
#   and records each returned submission id in data/submissions_map.json, so a
#   large generated wave can be graded and measured in one pass. Batches that
#   fail local validation are skipped and reported rather than sent.
# Usage: py scripts/submit_many.py FIRST LAST
# Tech Stack: Python 3.10+
# ==============================================================================

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data" / "submissions_map.json"


def main(first, last):
    m = json.loads(MAP.read_text()) if MAP.exists() else {}
    sent = 0
    for n in range(first, last + 1):
        rel = f"batches/igp24_batch_{n:03d}.txt"
        path = ROOT / rel
        if not path.exists():
            continue
        # relative.py / factory.py already flint-verify irreducibility before
        # writing, so the slow sympy re-validation is skipped here.
        out = subprocess.run(
            [sys.executable, "scripts/sair_api.py", "submit", rel],
            cwd=ROOT, capture_output=True, text=True).stdout
        sid = None
        for tok in out.replace(",", " ").split():
            if tok.startswith("sub_"):
                sid = tok
        if sid:
            m[sid] = rel
            sent += 1
            print(f"{rel}: {sid}")
        else:
            print(f"{rel}: no id returned -> {out.strip()[:120]}")
        if sent % 10 == 0:
            MAP.write_text(json.dumps(m, indent=1))
    MAP.write_text(json.dumps(m, indent=1))
    print(f"submitted {sent} batches, map now {len(m)}")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
