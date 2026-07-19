# ==============================================================================
# File: generate_submission.py
# Description: Builds submission.txt for IGP24 from structured constructions
#   that land on rare, low index transitive groups of degree 24. Random dense
#   polynomials collapse into S24 or A24, which every team already holds; the
#   value is in imprimitive and abelian fields, so this generator draws from
#   cyclotomic fields, polynomial compositions, and sparse trinomials, keeps
#   only irreducible monic degree 24 polynomials, and records the real root
#   count for provenance. Labels are computed by the official Magma verifier,
#   not here, so nothing claims a group it cannot prove.
# Tech Stack: Python 3.10+, SymPy, NumPy
# ==============================================================================

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import sympy as sp
from sympy import Poly, cyclotomic_poly, compose, factorint, totient

x = sp.symbols("x")

BASELINE_CSV = Path(__file__).resolve().parents[1] / "data" / "lmfdb_baseline.csv"

MAX_LINES = 1000
MAX_ABS_COEFF = 300         # keep coefficients (and discriminants) small
MAX_TRINOMIALS = 220        # trinomials only fill after the structured families


def coeffs_ascending(poly: Poly) -> list[int]:
    """Return the 25 integer coefficients a_0..a_24 in ascending powers."""
    c = [int(v) for v in reversed(poly.all_coeffs())]
    return c


def is_valid(c: list[int]) -> bool:
    """Monic degree 24, nonzero constant term, coefficients within bound."""
    if len(c) != 25 or c[24] != 1 or c[0] == 0:
        return False
    return all(abs(v) <= MAX_ABS_COEFF for v in c)


def real_root_count(c: list[int]) -> int:
    """Number of real roots, the signature r the verifier will report."""
    roots = np.roots([float(v) for v in reversed(c)])
    return int(np.sum(np.abs(roots.imag) < 1e-9))


def irreducible(c: list[int]) -> bool:
    p = Poly(list(reversed(c)), x, domain="ZZ")
    return p.is_irreducible


class Batch:
    """Collects candidate polynomials, deduplicated against mirrors."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.seen: set[tuple[int, ...]] = set()

    def key(self, c: list[int]) -> tuple[int, ...]:
        # x -> -x gives the same field; store the lexicographically smaller.
        mirror = [v * (-1) ** i for i, v in enumerate(c)]
        return min(tuple(c), tuple(mirror))

    def add(self, c: list[int], tag: str, primes: list[int] | None = None) -> bool:
        if not is_valid(c) or self.key(c) in self.seen:
            return False
        if not irreducible(c):
            return False
        self.seen.add(self.key(c))

        line = ",".join(str(v) for v in c)
        comment = f" # {tag}"
        if primes:
            # Reserved trailing token; only the list is compacted, the leading
            # space that separates it from the tag must stay.
            comment += " poly_disc_primes=" + str(primes).replace(" ", "")
        self.lines.append(line + comment)
        return True

    def exclude_baseline(self) -> int:
        """Seed the dedup set with every LMFDB baseline polynomial so a known
        field is never emitted as a discovery. Only new pairs can score."""
        if not BASELINE_CSV.exists():
            return 0
        count = 0
        with BASELINE_CSV.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                c = [int(v) for v in row["coeffs"].split(",")]
                if len(c) == 25:
                    self.seen.add(self.key(c))
                    count += 1
        return count

    def full(self) -> bool:
        return len(self.lines) >= MAX_LINES


def add_cyclotomic(batch: Batch) -> None:
    """Abelian fields: Phi_n with phi(n)=24. Rare groups, tiny discriminant."""
    for n in range(1, 400):
        if totient(n) != 24:
            continue
        c = coeffs_ascending(Poly(cyclotomic_poly(n, x), x))
        primes = sorted(factorint(n).keys())
        batch.add(c, f"cyclotomic_{n}", primes)


# Small monic polynomials per degree, used as links in a composition chain.
# A chain f1(f2(...(fj(x)))) with degrees multiplying to 24 realizes an
# imprimitive group whose block system mirrors the chain, so different chains
# and different links reach different transitive labels.
LINKS = {
    2: [[1, 0, 1], [-1, 0, 1], [-2, 0, 1], [-3, 0, 1], [1, 1, 1], [-1, 1, 1], [2, 1, 1]],
    3: [[-2, 0, 0, 1], [1, 0, 0, 1], [-1, -1, 0, 1], [1, -3, 0, 1], [-3, 0, 0, 1]],
    4: [[1, 0, 0, 0, 1], [-1, 0, 0, 0, 1], [1, 1, 0, 0, 1], [-2, 0, 0, 0, 1], [-1, 0, 1, 0, 1]],
    6: [[-1] + [0] * 5 + [1], [1] + [0] * 5 + [1], [1, 1] + [0] * 4 + [1], [-2] + [0] * 5 + [1]],
    8: [[-1] + [0] * 7 + [1], [1] + [0] * 7 + [1], [2] + [0] * 7 + [1]],
    12: [[-1] + [0] * 11 + [1], [1] + [0] * 11 + [1]],
}


def ordered_factorizations(n: int, parts: list[int] | None = None):
    """Every ordered product of factors >= 2 that multiplies to n."""
    parts = parts or []
    if n == 1:
        if len(parts) >= 2:
            yield list(parts)
        return
    for d in range(2, n + 1):
        if n % d == 0:
            yield from ordered_factorizations(n // d, parts + [d])


def compose_chain(degrees: list[int], picks: list[int]) -> Poly:
    """Fold links into f1(f2(...(fj(x)))) for the given degree chain."""
    cur = Poly(x, x, domain="ZZ")
    for deg, idx in zip(reversed(degrees), reversed(picks)):
        link = Poly(list(reversed(LINKS[deg][idx])), x, domain="ZZ")
        cur = compose(link, cur)
    return cur


def add_compositions(batch: Batch, per_chain: int = 72) -> None:
    for degrees in ordered_factorizations(24):
        if any(d not in LINKS for d in degrees):
            continue
        made = 0
        # Sweep the first link widely, later links lightly, to stay bounded.
        import itertools

        ranges = [range(len(LINKS[d])) for d in degrees]
        for picks in itertools.product(*ranges):
            h = compose_chain(list(degrees), list(picks))
            if h.degree() == 24:
                c = coeffs_ascending(h)
                if batch.add(c, "compose_" + "x".join(map(str, degrees))):
                    made += 1
            if made >= per_chain or batch.full():
                break
        if batch.full():
            return


def add_trinomials(batch: Batch) -> None:
    """Sparse x^24 + a*x^b + c: cheap coverage of primitive and large groups.
    Capped, and spread across many middle terms so they do not all collapse
    onto the same common group."""
    added = 0
    for b in range(1, 24):
        for a in (1, -1, 2, -2):
            for const in (1, -1, 2, -2, 3, -3):
                c = [0] * 25
                c[24] = 1
                c[b] += a
                c[0] += const
                if c[0] == 0:
                    continue
                if batch.add(c, f"trinomial_x{b}"):
                    added += 1
                if added >= MAX_TRINOMIALS or batch.full():
                    return


def main() -> None:
    batch = Batch()
    excluded = batch.exclude_baseline()
    print(f"baseline entries excluded from search: {excluded}")
    add_cyclotomic(batch)
    add_compositions(batch)
    add_trinomials(batch)

    with open("submission.txt", "w", encoding="ascii", newline="\n") as f:
        f.write("# IGP24 submission. Degree 24 monic irreducible polynomials,\n")
        f.write("# a_0,...,a_24 ascending. Constructions: cyclotomic abelian\n")
        f.write("# fields, compositions (imprimitive), and sparse trinomials.\n")
        for line in batch.lines:
            f.write(line + "\n")

    size = sum(len(l) + 1 for l in batch.lines)
    print(f"lines: {len(batch.lines)}  approx_bytes: {size}")


if __name__ == "__main__":
    main()
