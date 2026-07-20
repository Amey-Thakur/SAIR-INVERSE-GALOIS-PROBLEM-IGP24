# ==============================================================================
# File: factory.py
# Description: High-volume batch factory for IGP24. The leaderboard pays for
#   pairs no other team holds, so the factory optimizes diversity, not count:
#   it generates tens of thousands of structurally varied degree 24 fields
#   (random tower chains, root-sum composita, totally real towers for the
#   scarce high signature pairs), fingerprints each candidate's Galois group
#   by its Frobenius cycle types, and emits batches that contain exactly one
#   polynomial per distinct (group fingerprint, signature) cluster. A ledger
#   remembers every cluster ever submitted, so consecutive runs never spend a
#   line on a pair the team already holds.
# Usage: py scripts/factory.py [--batches N]
# Tech Stack: Python 3.10+, python-flint, SymPy, NumPy
# ==============================================================================

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import group_key, is_irreducible_deg24, real_roots

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "ledger.jsonl"
BASELINE = ROOT / "data" / "lmfdb_baseline.csv"
BATCH_DIR = ROOT / "batches"

MAX_ABS_COEFF = 10 ** 14      # keeps lines short and discriminants sane
BATCH_LINES = 1000

rng = random.Random(31415)    # seeded: every run is reproducible


# -- integer polynomial arithmetic (coeffs ascending) ----------------------

def polymul(a: list[int], b: list[int]) -> list[int]:
    out = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                out[i + j] += ai * bj
    return out


def compose(outer: list[int], inner: list[int]) -> list[int]:
    """outer(inner(x)) by Horner's rule."""
    result = [outer[-1]]
    for c in reversed(outer[:-1]):
        result = polymul(result, inner)
        result[0] += c
    return result


# -- link pools for tower chains -------------------------------------------

def quadratic_links():
    out = []
    for b in (0, 1, -1, 2, -2):
        for c in (1, -1, 2, -2, 3, -3, 5, -5, 7, -7):
            out.append([c, b, 1])
    return out


def link_pool(deg: int) -> list[list[int]]:
    if deg == 2:
        return quadratic_links()
    out = []
    mids = [deg // 2, 1] if deg > 2 else [1]
    for mid in dict.fromkeys(mids):
        for b in (0, 1, -1, 2, -2, 3, -3):
            for c in (1, -1, 2, -2, 3, -3):
                link = [0] * (deg + 1)
                link[deg] = 1
                link[mid] += b
                link[0] += c
                if link[0] != 0:
                    out.append(link)
    return out


LINKS = {d: link_pool(d) for d in (2, 3, 4, 6, 8, 12)}


def chain_shapes():
    """Every ordered factorization of 24 into parts from the link pool."""
    shapes = []

    def rec(n, parts):
        if n == 1:
            if len(parts) >= 2:
                shapes.append(tuple(parts))
            return
        for d in (2, 3, 4, 6, 8, 12):
            if n % d == 0:
                rec(n // d, parts + [d])

    rec(24, [])
    return shapes


SHAPES = chain_shapes()


# -- engines ---------------------------------------------------------------

def engine_towers(count: int):
    """Random tower chains: the deep well of imprimitive groups."""
    for _ in range(count):
        shape = rng.choice(SHAPES)
        poly = [0, 1]
        for deg in reversed(shape):
            poly = compose(rng.choice(LINKS[deg]), poly)
        yield poly, "tower_" + "x".join(map(str, shape))


def engine_composita(count: int):
    """Minimal polynomials of root sums: subdirect products, a family the
    tower engine cannot reach. Res_y(f(y), g(x - y)) via SymPy."""
    import sympy as sp

    x, y = sp.symbols("x y")
    made = 0
    attempts = 0
    pairs = [(2, 12), (3, 8), (4, 6), (6, 4)]
    while made < count and attempts < count * 8:
        attempts += 1
        da, db = rng.choice(pairs)
        f = rng.choice(LINKS[da])
        g = rng.choice(LINKS[db])
        fy = sum(c * y ** i for i, c in enumerate(f))
        gxy = sum(c * (x - y) ** i for i, c in enumerate(g))
        try:
            res = sp.Poly(sp.resultant(fy, gxy, y), x)
        except Exception:
            continue
        if res.degree() != 24:
            continue
        coeffs = [int(v) for v in reversed(res.all_coeffs())]
        lead = coeffs[24]
        if lead in (1, -1):
            if lead == -1:
                coeffs = [-c for c in coeffs]
            made += 1
            yield coeffs, f"compositum_{da}+{db}"


def engine_totally_real(count: int):
    """Towers engineered to keep every root real: high signature fields,
    where pairs are scarcest. A step to q(x^2 - c) doubles the degree, and
    every root stays real when c clears the smallest root of q. Choosing c
    right at that bar gives r = 24; ducking under it converts a few root
    pairs to complex ones and sweeps the intermediate signatures too."""
    import numpy as np

    # Degree 3 bases only: doubling reaches 24 from 3 (3, 6, 12, 24) but
    # never from 2 (2, 4, 8, 16, 32). Both cubics are cyclic and totally real.
    bases = [
        [-1, -3, 0, 1],   # x^3 - 3x - 1
        [1, -3, 0, 1],    # x^3 - 3x + 1
    ]
    made = 0
    while made < count:
        poly = rng.choice(bases)[:]
        ok = True
        while len(poly) - 1 < 24 and ok:
            roots = np.roots([float(c) for c in reversed(poly)])
            reals = roots.real[np.abs(roots.imag) < 1e-7]
            if reals.size == 0:
                ok = False
                break
            floor_c = int(np.ceil(-reals.min())) + 1
            c = floor_c + rng.choice((0, 0, 0, 1, 2, 4, -1, -2, -3))
            # q(x^2 - c): substitute the quadratic into the current stage.
            poly = compose(poly, [-c, 0, 1])
        if not ok or len(poly) - 1 != 24:
            continue
        made += 1
        yield poly, "totally_real"


# -- exclusions and ledger -------------------------------------------------

def mirror(coeffs):
    return tuple(v * (-1) ** i for i, v in enumerate(coeffs))


def canonical(coeffs):
    return min(tuple(coeffs), mirror(coeffs))


def load_baseline_fields():
    seen = set()
    with BASELINE.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            c = [int(v) for v in row["coeffs"].split(",")]
            if len(c) == 25:
                seen.add(canonical(c))
    return seen


def key_hash(key: frozenset) -> str:
    text = json.dumps(sorted(sorted(p) for p in key))
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def load_ledger():
    fields, clusters = set(), set()
    if LEDGER.exists():
        for raw in LEDGER.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            rec = json.loads(raw)
            fields.add(canonical([int(v) for v in rec["coeffs"].split(",")]))
            clusters.add((rec["key"], rec["r"]))
    return fields, clusters


def seed_ledger_from_submission():
    """First run only: fold the already submitted 840 into the ledger so the
    factory never re-covers ground the team already holds."""
    if LEDGER.exists():
        return
    LEDGER.parent.mkdir(exist_ok=True)
    sub = ROOT / "submission.txt"
    if not sub.exists():
        return
    with LEDGER.open("w", encoding="utf-8") as out:
        for raw in sub.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            coeffs = [int(v) for v in raw.split("#", 1)[0].strip().split(",")]
            rec = {
                "coeffs": ",".join(map(str, coeffs)),
                "key": key_hash(group_key(coeffs)),
                "r": real_roots(coeffs),
                "batch": "submission_2026-07-18",
            }
            out.write(json.dumps(rec) + "\n")


# -- batch assembly --------------------------------------------------------

def build_batches(n_batches: int):
    seed_ledger_from_submission()
    baseline_fields = load_baseline_fields()
    ledger_fields, ledger_clusters = load_ledger()

    plan = [
        (engine_totally_real, 6000),
        (engine_composita, 1500),
        (engine_towers, 70000),
    ]

    picked = []            # (coeffs, tag, keyhash, r)
    picked_clusters = set(ledger_clusters)
    seen_fields = set(baseline_fields) | ledger_fields
    target = n_batches * BATCH_LINES
    started = time.time()
    stats = {"raw": 0, "irreducible": 0, "novel": 0}

    for engine, count in plan:
        if len(picked) >= target:
            break
        for coeffs, tag in engine(count):
            stats["raw"] += 1
            if stats["raw"] % 5000 == 0:
                print(f"  raw {stats['raw']}, kept {len(picked)}, "
                      f"{time.time() - started:.0f}s", flush=True)
            if len(picked) >= target:
                break
            if any(abs(c) > MAX_ABS_COEFF for c in coeffs):
                continue
            key = canonical(coeffs)
            if key in seen_fields:
                continue
            seen_fields.add(key)
            if not is_irreducible_deg24(coeffs):
                continue
            stats["irreducible"] += 1
            kh = key_hash(group_key(coeffs))
            r = real_roots(coeffs)
            if (kh, r) in picked_clusters:
                continue
            picked_clusters.add((kh, r))
            stats["novel"] += 1
            picked.append((coeffs, tag, kh, r))

    # Rare signatures first: high r pairs have the least competition.
    picked.sort(key=lambda item: -item[3])

    BATCH_DIR.mkdir(exist_ok=True)
    written = []
    with LEDGER.open("a", encoding="utf-8") as ledger:
        for b in range(n_batches):
            chunk = picked[b * BATCH_LINES:(b + 1) * BATCH_LINES]
            if not chunk:
                break
            name = f"igp24_batch_{b + 1:03d}.txt"
            path = BATCH_DIR / name
            with path.open("w", encoding="ascii", newline="\n") as out:
                out.write("# IGP24 batch: one polynomial per distinct "
                          "(group fingerprint, signature) cluster.\n")
                for coeffs, tag, kh, r in chunk:
                    line = ",".join(map(str, coeffs))
                    out.write(f"{line} # {tag} r={r}\n")
                    ledger.write(json.dumps({
                        "coeffs": ",".join(map(str, coeffs)),
                        "key": kh, "r": r, "batch": name,
                    }) + "\n")
            written.append((name, len(chunk)))

    print(f"raw {stats['raw']}, irreducible {stats['irreducible']}, "
          f"novel clusters {stats['novel']}")
    for name, count in written:
        print(f"wrote batches/{name}: {count} lines")
    print(f"total time {time.time() - started:.0f}s")


if __name__ == "__main__":
    n = 10
    if "--batches" in sys.argv:
        n = int(sys.argv[sys.argv.index("--batches") + 1])
    build_batches(n)
