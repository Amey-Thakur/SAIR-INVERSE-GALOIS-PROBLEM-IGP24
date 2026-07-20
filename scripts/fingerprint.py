# ==============================================================================
# File: fingerprint.py
# Description: Group-level fingerprints for degree 24 polynomials without
#   Magma. Factoring f mod p gives the cycle type of the Frobenius element at
#   p; by Chebotarev the set of cycle types seen across many primes
#   approximates the set of cycle types of the Galois group itself. Two
#   polynomials with different fingerprints lie in different groups, so the
#   fingerprint deduplicates candidates by group before a single submission
#   line is spent. Requires python-flint for speed.
# Usage: imported by factory.py
# Tech Stack: Python 3.10+, python-flint, NumPy
# ==============================================================================

from __future__ import annotations

import flint
import numpy as np

# Primes above the degree, so no accidental small-prime artifacts. 24 samples
# is enough to see every cycle type of density above a few percent.
PRIMES = [101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157,
          163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227]


def is_irreducible_deg24(coeffs_asc: list[int]) -> bool:
    """Exact irreducibility over Z via flint factorization."""
    if len(coeffs_asc) != 25 or coeffs_asc[0] == 0 or coeffs_asc[24] != 1:
        return False
    _, factors = flint.fmpz_poly(coeffs_asc).factor()
    return len(factors) == 1 and factors[0][1] == 1 and factors[0][0].degree() == 24


def cycle_pattern(coeffs_asc: list[int], p: int) -> tuple | None:
    """Sorted factor-degree pattern of f mod p, or None when f mod p is not
    squarefree (a ramified or unlucky prime, no Frobenius information)."""
    f = flint.nmod_poly([c % p for c in coeffs_asc], p)
    if f.degree() != 24 or f.gcd(f.derivative()).degree() != 0:
        return None
    _, factors = f.factor()
    degrees = []
    for poly, mult in factors:
        degrees.extend([poly.degree()] * mult)
    return tuple(sorted(degrees))


def group_key(coeffs_asc: list[int]) -> frozenset:
    """The set of cycle types observed across the sample primes. Fields with
    the same Galois group share this set almost surely; fields in different
    groups almost always differ somewhere in it."""
    patterns = set()
    for p in PRIMES:
        pat = cycle_pattern(coeffs_asc, p)
        if pat is not None:
            patterns.add(pat)
    return frozenset(patterns)


def real_roots(coeffs_asc: list[int]) -> int:
    """Signature r: the number of real roots, always even in degree 24."""
    roots = np.roots([float(c) for c in reversed(coeffs_asc)])
    r = int(np.sum(np.abs(roots.imag) < 1e-7))
    return r if r % 2 == 0 else r - 1
