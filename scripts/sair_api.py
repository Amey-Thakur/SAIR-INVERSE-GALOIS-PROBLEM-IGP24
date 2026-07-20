# ==============================================================================
# File: sair_api.py
# Description: The feedback loop with the competition server. Three commands:
#   `remaining` saves the (24Tt, r) pairs no participant team has claimed
#   yet (each is worth a full point to its first finder), `submit` posts one
#   or more batch files, and `results` lists recent submissions with their
#   acceptance counts. Requires an API key with competition.read (and
#   competition.write for submit) in the SAIR_API_KEY environment variable.
# Usage: py scripts/sair_api.py remaining
#        py scripts/sair_api.py submit batches/igp24_batch_001.txt [...]
#        py scripts/sair_api.py results
# Tech Stack: Python 3.10+, Requests
# ==============================================================================

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = "https://api.sair.foundation/api/public/v1/competitions/igp24"
ROOT = Path(__file__).resolve().parents[1]


def _headers():
    key = os.environ.get("SAIR_API_KEY", "")
    if not key:
        sys.exit("SAIR_API_KEY is not set. Create one at "
                 "https://id.sair.foundation/profile/api-keys and export it.")
    return {"Authorization": f"Bearer {key}"}


def remaining():
    """Page through every unclaimed (24Tt, r) pair and save the list."""
    pairs, cursor = [], None
    while True:
        params = {"limit": 5000}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(f"{BASE}/remaining-pairs", headers=_headers(),
                            params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        page = data.get("items") or data.get("pairs") or data.get("data") or []
        pairs.extend(page)
        cursor = data.get("nextCursor") or data.get("cursor")
        if not cursor or not page:
            break

    out = ROOT / "data" / "remaining_pairs.json"
    out.write_text(json.dumps(pairs, indent=1), encoding="utf-8")
    print(f"unclaimed pairs: {len(pairs)}, saved to {out.relative_to(ROOT)}")


def submit(paths):
    """Post each batch file as one submission. One POST is one submission
    against the daily cap, no matter how many polynomials it carries."""
    for path in paths:
        lines = [
            s.strip() for s in Path(path).read_text(encoding="utf-8").splitlines()
            if s.strip() and not s.strip().startswith("#")
        ]
        resp = requests.post(
            f"{BASE}/submissions", headers=_headers(),
            json={"payload": {"polynomials": lines}}, timeout=120,
        )
        status = "ok" if resp.ok else f"HTTP {resp.status_code}"
        print(f"{path}: {len(lines)} polynomials, {status}")
        if not resp.ok:
            print(" ", resp.text[:300])
            break
        time.sleep(2)   # be polite to the evaluator queue


def results():
    resp = requests.get(f"{BASE}/submissions/me", headers=_headers(),
                        params={"limit": 20}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items") or data.get("submissions") or data.get("data") or []
    for item in items:
        print(json.dumps(item, indent=1)[:400])
        print("-" * 40)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("remaining", "submit", "results"):
        sys.exit(__doc__ or "usage: sair_api.py remaining|submit|results")
    if sys.argv[1] == "remaining":
        remaining()
    elif sys.argv[1] == "submit":
        if len(sys.argv) < 3:
            sys.exit("submit needs at least one batch file")
        submit(sys.argv[2:])
    else:
        results()


if __name__ == "__main__":
    main()
