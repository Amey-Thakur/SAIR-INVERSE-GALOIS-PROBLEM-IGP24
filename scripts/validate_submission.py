# ==============================================================================
# File: validate_submission.py
# Description: Independent gate on submission.txt, parsing each line the way the
#   official evaluator does and re-checking every constraint from scratch:
#   exactly 25 integer coefficients before any trailing comment, monic, nonzero
#   constant term, coefficient gcd 1, irreducible over Q, no duplicate field,
#   valid poly_disc_primes hints, and the 1,000,000 byte ceiling. Nothing here
#   trusts the generator; a line ships only if this file re-derives it as valid.
# Tech Stack: Python 3.10+, SymPy
# ==============================================================================

from __future__ import annotations

import re
import sys
from math import gcd
from pathlib import Path

import numpy as np
import sympy as sp

x = sp.symbols("x")
PRIMES_RE = re.compile(r"poly_disc_primes=\[([0-9,]*)\]")


def parse_coeffs(line: str) -> list[int]:
    body = line.split("#", 1)[0].strip()
    return [int(p) for p in body.split(",")]


def validate() -> int:
    path = Path("submission.txt")
    raw = path.read_bytes()
    if len(raw) > 1_000_000:
        print(f"FAIL: file is {len(raw)} bytes, over the 1,000,000 limit")
        return 1

    lines = path.read_text(encoding="ascii").splitlines()
    seen: set[tuple[int, ...]] = set()
    data = 0
    r_hist: dict[int, int] = {}

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        data += 1

        c = parse_coeffs(s)
        if len(c) != 25:
            print(f"FAIL line {i}: {len(c)} coefficients, need 25")
            return 1
        if c[24] != 1:
            print(f"FAIL line {i}: not monic")
            return 1
        if c[0] == 0:
            print(f"FAIL line {i}: zero constant term")
            return 1
        if gcd(*[abs(v) for v in c]) != 1:
            print(f"FAIL line {i}: coefficient gcd is not 1")
            return 1

        poly = sp.Poly(list(reversed(c)), x, domain="ZZ")
        if poly.degree() != 24 or not poly.is_irreducible:
            print(f"FAIL line {i}: reducible or wrong degree")
            return 1

        mirror = tuple(v * (-1) ** j for j, v in enumerate(c))
        key = min(tuple(c), mirror)
        if key in seen:
            print(f"FAIL line {i}: duplicate field (mirror of an earlier line)")
            return 1
        seen.add(key)

        m = PRIMES_RE.search(s)
        if m and m.group(1):
            primes = [int(p) for p in m.group(1).split(",")]
            if any(p <= 1 for p in primes) or primes != sorted(set(primes)):
                print(f"FAIL line {i}: bad poly_disc_primes hint")
                return 1

        roots = np.roots([float(v) for v in reversed(c)])
        r = int(np.sum(np.abs(roots.imag) < 1e-9))
        r_hist[r] = r_hist.get(r, 0) + 1

    print(f"PASS: {data} polynomials, all irreducible monic degree 24, {len(raw)} bytes")
    print("real-root (signature) spread r -> count:",
          {k: r_hist[k] for k in sorted(r_hist)})
    return 0


if __name__ == "__main__":
    sys.exit(validate())
