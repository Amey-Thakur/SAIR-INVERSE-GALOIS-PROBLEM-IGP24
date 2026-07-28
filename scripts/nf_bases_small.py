# ==============================================================================
# File: nf_bases_small.py
# Description: Downloads small degree base fields from the LMFDB number field
#   API for the class field sweep: quartics, sextics, and octics, a handful
#   per Galois type at the smallest discriminants, totally real pulls first
#   so every archimedean pattern is reachable. Output data/nf_small.jsonl,
#   one line per (degree, galois_label) group. Resumable.
# Usage: py scripts/nf_bases_small.py
# Tech Stack: Python 3.10+, curl via subprocess
# ==============================================================================

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "nf_small.jsonl"
API = "https://www.lmfdb.org/api/nf_fields/"
FIELDS = "coeffs,galois_label,r2,disc_abs"
GROUP_COUNTS = {4: 5, 6: 16, 8: 50}


def fetch(query):
    url = f"{API}?{query}&_format=json&_fields={FIELDS}&_sort=disc_abs"
    for attempt in range(10):
        try:
            out = subprocess.run(
                ["curl", "-sL", "--max-time", "120", url],
                capture_output=True, text=True, timeout=140,
            ).stdout
            return json.loads(out).get("data", [])
        except Exception:
            time.sleep(min(15, 3 + attempt * 2))
    return None


def main():
    done = set()
    if OUT.exists():
        for raw in OUT.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                done.add(json.loads(raw)["label"])
    print(f"already have {len(done)} groups", flush=True)

    with OUT.open("a", encoding="utf-8") as fh:
        for deg, count in GROUP_COUNTS.items():
            for t in range(1, count + 1):
                label = f"{deg}T{t}"
                if label in done:
                    continue
                real_rows = fetch(f"degree={deg}&galois_label={label}&r2=0") or []
                any_rows = fetch(f"degree={deg}&galois_label={label}") or []
                seen, fields = set(), []
                for r in real_rows[:25] + any_rows[:40]:
                    key = tuple(r["coeffs"])
                    if key not in seen:
                        seen.add(key)
                        fields.append({"coeffs": r["coeffs"], "r2": r["r2"],
                                       "disc_abs": r.get("disc_abs")})
                fh.write(json.dumps({"label": label, "degree": deg,
                                     "fields": fields}) + "\n")
                fh.flush()
                done.add(label)
                time.sleep(1.0)
            print(f"degree {deg} complete", flush=True)
    print(f"done: {len(done)} groups")


if __name__ == "__main__":
    main()
