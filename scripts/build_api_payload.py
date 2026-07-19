# ==============================================================================
# File: build_api_payload.py
# Description: Turns submission.txt into api_payload.json for the IGP24 API.
#   Each data line becomes one entry of payload.polynomials exactly as written,
#   trailing comment preserved (the API keeps trailing comments and honors the
#   reserved poly_disc_primes form). Full line comments are dropped.
# Usage: py scripts/build_api_payload.py
# Tech Stack: Python 3.10+
# ==============================================================================

import json
from pathlib import Path


def main() -> None:
    lines = Path("submission.txt").read_text(encoding="ascii").splitlines()
    polys = [s.strip() for s in lines if s.strip() and not s.startswith("#")]

    payload = {"payload": {"polynomials": polys}}
    Path("scripts/api_payload.json").write_text(
        json.dumps(payload, separators=(",", ":")) + "\n", encoding="ascii"
    )
    print(f"api_payload.json written with {len(polys)} polynomials")


if __name__ == "__main__":
    main()
