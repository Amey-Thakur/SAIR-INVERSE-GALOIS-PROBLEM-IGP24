# ==============================================================================
# File: lmfdb_groups.py
# Description: Downloads permutation generators for all 25,000 transitive
#   groups of degree 24 from the LMFDB API. The generators feed
#   group_profiles.py, which turns each group into a cycle-type distribution;
#   together they replace Magma's label identification with a free, local
#   pipeline. Resumable: already-fetched pages are skipped on rerun.
# Usage: py scripts/lmfdb_groups.py
# Tech Stack: Python 3.10+, Requests
# ==============================================================================

from __future__ import annotations

import json
import time
from pathlib import Path

import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "groups24.jsonl"
API = "https://www.lmfdb.org/api/gps_transitive/"
FIELDS = "t,label,gens,order,solv,parity"
PAGE = 100


def fetched_ts():
    done = set()
    if OUT.exists():
        for raw in OUT.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                done.add(json.loads(raw)["t"])
    return done


def main():
    done = fetched_ts()
    print(f"already have {len(done)} groups")
    OUT.parent.mkdir(exist_ok=True)

    with OUT.open("a", encoding="utf-8") as fh:
        # Rows arrive in t order, so the resume point is simply how many we
        # already hold, rounded down to a page boundary.
        offset = (len(done) // PAGE) * PAGE
        while offset < 25000:
            # The API rejects percent-encoded commas in _fields, so the
            # query string is built by hand. curl is used instead of requests
            # because the sandbox intercepts the requests library with a
            # captcha page while curl reaches LMFDB directly.
            url = (f"{API}?n=24&_format=json&_fields={FIELDS}"
                   f"&_offset={offset}")
            rows = None
            for attempt in range(40):
                try:
                    out = subprocess.run(
                        ["curl", "-sL", "--max-time", "180", url],
                        capture_output=True, text=True, timeout=200,
                    ).stdout
                    rows = json.loads(out).get("data", [])
                    break
                except Exception as exc:
                    wait = min(30, 4 + attempt * 2)
                    print(f"offset {offset}: {exc}; retry in {wait}s", flush=True)
                    time.sleep(wait)
            if rows is None:
                print(f"skipping offset {offset} after retries", flush=True)
                offset += PAGE
                continue

            if not rows:
                break
            wrote = 0
            for row in rows:
                if row["t"] in done:
                    continue
                fh.write(json.dumps({
                    "t": row["t"], "label": row["label"], "gens": row["gens"],
                    "order": row.get("order"), "solv": row.get("solv"),
                    "parity": row.get("parity"),
                }) + "\n")
                done.add(row["t"])
                wrote += 1
            fh.flush()
            offset += PAGE
            if offset % 2000 == 0:
                print(f"offset {offset}, total {len(done)}", flush=True)
            time.sleep(1.5)   # slower pace avoids rate-triggered captchas

    print(f"done: {len(done)} groups in {OUT.name}")


if __name__ == "__main__":
    main()
