# ==============================================================================
# File: relative.py
# Description: Relative quadratic extension engine. Every earlier engine glued
#   independent fields, which yields split (direct product style) groups, and
#   the audit showed those are all crowded. This engine instead adjoins the
#   square root of an element theta INSIDE a degree-12 field K, producing
#   twisted imprimitive degree-24 groups the compositum families cannot reach.
#   Exact arithmetic without resultants: the minimal polynomial of sqrt(theta)
#   is h(x^2), where h is the characteristic polynomial of the multiplication
#   by theta matrix on Z[y]/(f). Signature control is exact: r = 2j, where j
#   counts real embeddings of K at which theta is positive, and a constant
#   shift places theta's sign pattern at any wanted j. Candidates are kept
#   only when their Frobenius fingerprint is new to the ledger (tier A) or
#   known at a new signature (tier B).
# Usage: py scripts/relative.py [minutes]
# Tech Stack: Python 3.10+, python-flint, NumPy
# ==============================================================================

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factory as F
from fingerprint import group_key, is_irreducible_deg24, real_roots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "batches"
MAX_ABS = 10 ** 24
rng = random.Random(31415)

# Signature demand: overall unclaimed pair counts by r, with a small floor so
# rare signatures still appear.
R_WEIGHT = {0: 1768, 2: 50, 4: 1504, 6: 200, 8: 3007, 10: 50, 12: 3073,
            14: 50, 16: 5953, 18: 50, 20: 3441, 22: 200, 24: 5234}

try:
    from flint import fmpz_mat

    def charpoly12(mat):
        return [int(c) for c in fmpz_mat(mat).charpoly().coeffs()]
except Exception:
    import sympy

    def charpoly12(mat):
        lam = sympy.symbols("lam")
        poly = sympy.Matrix(mat).charpoly(lam)
        return [int(c) for c in reversed(poly.all_coeffs())]


def mat_mul(a, b):
    n = len(a)
    return [[sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)]
            for i in range(n)]


class Base:
    def __init__(self, label, coeffs):
        self.label = label
        self.f = coeffs                       # ascending, len 13, monic
        n = 12
        comp = [[0] * n for _ in range(n)]
        for i in range(1, n):
            comp[i][i - 1] = 1
        for i in range(n):
            comp[i][n - 1] = -coeffs[i]
        self.pows = [None] * n                # companion matrix powers
        ident = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
        self.pows[0] = ident
        for k in range(1, n):
            self.pows[k] = mat_mul(self.pows[k - 1], comp)
        roots = np.roots(list(reversed(coeffs)))
        real = sorted(float(z.real) for z in roots if abs(z.imag) < 1e-9)
        self.emb = np.array([[y ** k for k in range(n)] for y in real])
        self.r1 = len(real)

    def theta_at(self, c):
        return self.emb @ np.array(c, dtype=float)


def theta_for_j(base, j):
    """Sample theta positive at exactly j real embeddings of the base."""
    for _ in range(30):
        c = [0] * 12
        for pos in rng.sample(range(1, 12), rng.randint(1, 4)):
            c[pos] = rng.choice([-3, -2, -1, 1, 2, 3])
        vals = sorted(base.theta_at(c), reverse=True)
        if j == 0:
            lo, hi = None, -vals[0]
        elif j == base.r1:
            lo, hi = -vals[-1], None
        else:
            lo, hi = -vals[j - 1], -vals[j]
        if lo is None:
            shift = int(np.floor(hi)) - 1 if hi is not None else 0
        elif hi is None:
            shift = int(np.ceil(lo)) + 1
        else:
            shift = int(np.floor(hi))
            if not lo < shift <= hi - 1e-9 and not lo < shift:
                continue
            if shift <= lo:
                continue
        c[0] += shift
        vals = base.theta_at(c)
        if sum(1 for v in vals if v > 1e-9) == j and all(abs(v) > 1e-9 for v in vals):
            return c
    return None


def minpoly_sqrt(base, c):
    n = 12
    mat = [[sum(c[k] * base.pows[k][i][j] for k in range(n) if c[k])
            for j in range(n)] for i in range(n)]
    h = charpoly12(mat)                       # ascending, monic, len 13
    if h[0] == 0:
        return None
    out = [0] * 25
    for i, v in enumerate(h):
        out[2 * i] = v
    return out


def main(minutes=40.0):
    groups = []
    for raw in (ROOT / "data" / "nf12.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            groups.append(json.loads(raw))
    print(f"bases: {len(groups)} groups", flush=True)

    keys_seen, pairs_seen = set(), set()
    for raw in (ROOT / "data" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rec = json.loads(raw)
            keys_seen.add(rec["key"])
            if "r" in rec:
                pairs_seen.add((rec["key"], rec["r"]))
    print(f"ledger: {len(keys_seen)} fingerprints", flush=True)

    bases = []
    for g in groups:
        for fld in g["fields"][:6]:
            try:
                bases.append(Base(g["label"], fld["coeffs"]))
            except Exception:
                pass
    rng.shuffle(bases)
    print(f"bases built: {len(bases)}", flush=True)

    r_pool = [r for r, w in R_WEIGHT.items() for _ in range(max(1, w // 50))]
    tier_a, tier_b = [], []
    claimed = set()
    started = time.time()
    tried = 0
    while time.time() - started < minutes * 60:
        base = rng.choice(bases)
        r_want = rng.choice(r_pool)
        if r_want > 2 * base.r1:
            continue
        c = theta_for_j(base, r_want // 2)
        if c is None:
            continue
        coeffs = minpoly_sqrt(base, c)
        tried += 1
        if coeffs is None or max(abs(v) for v in coeffs) > MAX_ABS:
            continue
        key = F.canonical(coeffs)
        if not is_irreducible_deg24(coeffs):
            continue
        kh = F.key_hash(group_key(coeffs))
        r = real_roots(coeffs)
        if (kh, r) in pairs_seen or (kh, r) in claimed:
            continue
        claimed.add((kh, r))
        row = (coeffs, f"rel12 base={base.label} r={r}", kh, r)
        if kh not in keys_seen:
            tier_a.append(row)
        else:
            tier_b.append(row)
        if tried % 500 == 0:
            print(f"  {int(time.time()-started)}s: tried {tried}, "
                  f"tierA {len(tier_a)}, tierB {len(tier_b)}", flush=True)

    print(f"total: tried {tried}, tierA {len(tier_a)} new-fingerprint, "
          f"tierB {len(tier_b)} new-signature", flush=True)
    rows = tier_a + tier_b
    if not rows:
        return
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    idx = max(existing, default=0) + 1
    ledger = (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8")
    for start in range(0, len(rows), 1000):
        chunk = rows[start:start + 1000]
        name = f"igp24_batch_{idx:03d}.txt"
        with (OUT / name).open("w", encoding="ascii", newline="\n") as fh:
            fh.write("# IGP24 relative extension wave: K(sqrt(theta)) over "
                     "degree-12 bases.\n")
            for coeffs, tag, kh, r in chunk:
                fh.write(",".join(map(str, coeffs)) + f" # {tag}\n")
        for coeffs, tag, kh, r in chunk:
            ledger.write(json.dumps({
                "coeffs": ",".join(map(str, coeffs)),
                "key": kh, "r": r, "batch": name,
            }) + "\n")
        print(f"wrote batches/{name}: {len(chunk)} lines", flush=True)
        idx += 1
    ledger.close()


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 40.0)
