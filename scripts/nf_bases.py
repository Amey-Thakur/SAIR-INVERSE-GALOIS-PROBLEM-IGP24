# ==============================================================================
# File: nf_bases.py
# Description: Downloads degree-12 base fields from the LMFDB number field
#   API, up to 100 per transitive group 12T1..12T301, totally real first
#   (r2 = 0) with a fallback to any signature when a group has no totally
#   real field. These bases feed relative.py, which builds degree-24 fields
#   as relative quadratic extensions K(sqrt(theta)). Resumable: groups
#   already present in the output are skipped on rerun.
# Usage: py scripts/nf_bases.py
# Tech Stack: Python 3.10+, curl via subprocess
# ==============================================================================

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "nf12.jsonl"
API = "https://www.lmfdb.org/api/nf_fields/"
FIELDS = "coeffs,galois_label,r2,disc_abs"


def fetch(query):
    url = f"{API}?{query}&_format=json&_fields={FIELDS}&_sort=disc_abs"
    for attempt in range(12):
        try:
            out = subprocess.run(
                ["curl", "-sL", "--max-time", "120", url],
                capture_output=True, text=True, timeout=140,
            ).stdout
            return json.loads(out).get("data", [])
        except Exception:
            time.sleep(min(20, 3 + attempt * 2))
    return None


def main():
    done = set()
    if OUT.exists():
        for raw in OUT.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                done.add(json.loads(raw)["label"])
    print(f"already have {len(done)} groups", flush=True)

    with OUT.open("a", encoding="utf-8") as fh:
        for t in range(1, 302):
            label = f"12T{t}"
            if label in done:
                continue
            rows = fetch(f"degree=12&galois_label={label}&r2=0")
            if not rows:
                rows = fetch(f"degree=12&galois_label={label}")
            if rows is None:
                print(f"{label}: unreachable, skipped", flush=True)
                continue
            fh.write(json.dumps({
                "label": label,
                "fields": [{"coeffs": r["coeffs"], "r2": r["r2"],
                            "disc_abs": r.get("disc_abs")} for r in rows[:100]],
            }) + "\n")
            fh.flush()
            done.add(label)
            if t % 25 == 0:
                print(f"{label}: total groups {len(done)}", flush=True)
            time.sleep(1.2)
    print(f"done: {len(done)} groups in {OUT.name}")


if __name__ == "__main__":
    main()
