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

MAX_ABS_COEFF = 10 ** 18      # keeps lines short and discriminants sane
BATCH_LINES = 1000

rng = random.Random(16180)    # seeded: every run is reproducible


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
    for b in (0, 1, -1, 2, -2, 3, -3):
        for c in (1, -1, 2, -2, 3, -3, 5, -5, 6, -6, 7, -7, 10, -10, 11, -11):
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


def engine_compose(count: int):
    """Two-factor compositions f(g(x)) with a structured outer polynomial:
    a cyclotomic or small-group f keeps the block action non-generic, which
    lands these in the mid-index zone more often than a random tower."""
    import sympy as sp
    from sympy import cyclotomic_poly

    x = sp.symbols("x")
    outers = {}
    for deg in (2, 3, 4, 6):
        outers[deg] = [list(link) for link in LINKS[deg]]
    for n in range(3, 20):
        c = [int(v) for v in reversed(sp.Poly(cyclotomic_poly(n, x), x).all_coeffs())]
        if len(c) - 1 in outers:
            outers[len(c) - 1].append(c)

    for _ in range(count):
        m, k = rng.choice([(2, 12), (3, 8), (4, 6), (6, 4)])
        f = rng.choice(outers[m])
        inner = [0] * (k + 1)
        inner[k] = 1
        inner[0] = rng.choice([c for c in range(-6, 7) if c])
        if rng.random() < 0.5:
            inner[rng.randrange(1, k)] += rng.choice((1, -1, 2, -2))
        poly = compose(f, inner)
        if len(poly) == 25 and poly[0] != 0:
            yield poly, f"compose_{m}x{k}"


def _small_field_pool():
    """Small monic irreducible base polynomials by degree, mixing the link
    pool with cyclotomic and structured pieces. Cyclotomic and other
    small-group components are what steer composita into the structured
    mid-index solvable groups that carry the unclaimed pairs."""
    import sympy as sp
    from sympy import cyclotomic_poly

    x = sp.symbols("x")
    pool = {d: [list(link) for link in LINKS[d]] for d in LINKS}
    for n in range(3, 60):
        c = [int(v) for v in reversed(sp.Poly(cyclotomic_poly(n, x), x).all_coeffs())]
        d = len(c) - 1
        if d in pool:
            pool[d].append(c)
    # A few named structured cubics and quartics with small Galois groups.
    pool[3] += [[-1, -3, 0, 1], [1, -3, 0, 1], [-1, -4, 0, 1], [1, 0, -1, 1]]
    pool[4] += [[1, 0, 0, 0, 1], [1, 0, 1, 0, 1], [-1, 0, -1, 0, 1], [4, 0, 1, 0, 1]]
    pool[2] += [[-2, 0, 1], [-3, 0, 1], [-5, 0, 1], [-6, 0, 1], [2, 2, 1]]
    return pool


def _resultant_sum(f, g, mult=1):
    """Minimal polynomial of alpha + mult*beta, alpha a root of f, beta of g,
    via Res_y(f(y), g((x - y)/mult)) cleared of denominators."""
    import sympy as sp
    x, y = sp.symbols("x y")
    db = len(g) - 1
    fy = sum(c * y ** i for i, c in enumerate(f))
    gxy = sum(c * (x - y) ** i * mult ** (db - i) for i, c in enumerate(g))
    return sp.Poly(sp.resultant(fy, gxy, y), x)


def _resultant_prod(f, g):
    """Minimal polynomial of alpha * beta via the homogenized resultant."""
    import sympy as sp
    x, y = sp.symbols("x y")
    db = len(g) - 1
    fy = sum(c * y ** i for i, c in enumerate(f))
    gxy = sum(c * x ** i * y ** (db - i) for i, c in enumerate(g))
    return sp.Poly(sp.resultant(fy, gxy, y), x)


def _monic_int(poly):
    """Return ascending integer coefficients of a degree 24 monic result, or
    None if the polynomial is not usable."""
    if poly is None or poly.degree() != 24:
        return None
    coeffs = [int(v) for v in reversed(poly.all_coeffs())]
    lead = coeffs[24]
    if lead == -1:
        coeffs = [-c for c in coeffs]
    elif lead != 1:
        return None
    return coeffs if coeffs[0] != 0 else None


def engine_composita(count: int):
    """Root-sum and root-product fields, in pairs and triples, with scaled
    combinations. This family reaches the structured mid-index solvable
    groups at roughly a 57 percent rate against 1.6 percent for towers, so
    it is now the primary engine. Triples and scalings multiply the reach
    into groups no pair compositum lands on."""
    pool = _small_field_pool()
    pairs = [(2, 12), (3, 8), (4, 6), (6, 4), (8, 3), (12, 2)]
    triples = [(2, 2, 6), (2, 3, 4), (2, 6, 2), (3, 2, 4), (4, 3, 2),
               (2, 2, 2, 3), (2, 4, 3), (6, 2, 2), (4, 2, 3), (3, 4, 2)]

    made = 0
    attempts = 0
    while made < count and attempts < count * 10:
        attempts += 1
        roll = rng.random()
        try:
            if roll < 0.45:
                da, db = rng.choice(pairs)
                f, g = rng.choice(pool[da]), rng.choice(pool[db])
                if rng.random() < 0.5:
                    mult = rng.choice((1, 1, 2, 3))
                    coeffs = _monic_int(_resultant_sum(f, g, mult))
                    kind = f"sum{mult}_{da}+{db}"
                else:
                    coeffs = _monic_int(_resultant_prod(f, g))
                    kind = f"prod_{da}x{db}"
            else:
                shape = rng.choice(triples)
                # Fold roots left to right: build the running sum field, then
                # add the next root, keeping only degree-24 endpoints.
                degs = list(shape)
                acc = rng.choice(pool[degs[0]])
                good = True
                for d in degs[1:]:
                    nxt = rng.choice(pool[d])
                    mult = rng.choice((1, 1, 2))
                    poly = _resultant_sum(acc, nxt, mult)
                    acc = [int(v) for v in reversed(poly.all_coeffs())]
                    if len(acc) - 1 > 24:
                        good = False
                        break
                if not good:
                    continue
                import sympy as sp
                coeffs = _monic_int(sp.Poly(list(reversed(acc)), sp.symbols("x")))
                kind = "tri_" + "x".join(map(str, shape))
        except Exception:
            continue
        if coeffs is None:
            continue
        made += 1
        yield coeffs, f"compositum_{kind}"


def engine_totally_real(count: int):
    """Towers engineered to keep every root real: high signature fields,
    where pairs are scarcest. A step to q(x^2 - c) doubles the degree, and
    every root stays real when c clears the smallest root of q. Choosing c
    right at that bar gives r = 24; ducking under it converts a few root
    pairs to complex ones and sweeps the intermediate signatures too."""
    import numpy as np

    # Degree 3 bases only: doubling reaches 24 from 3 (3, 6, 12, 24) but
    # never from 2 (2, 4, 8, 16, 32). The first two cubics are cyclic, the
    # others have square-free positive discriminant (S3, still totally real),
    # which seeds a different family of wreath towers.
    bases = [
        [-1, -3, 0, 1],   # x^3 - 3x - 1, disc 81
        [1, -3, 0, 1],    # x^3 - 3x + 1, disc 81
        [-1, -4, 0, 1],   # x^3 - 4x - 1, disc 229
        [-2, -4, 0, 1],   # x^3 - 4x - 2, disc 148
        [-1, -7, 0, 1],   # x^3 - 7x - 1, disc 1345
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
            # At or above the bar keeps r = 24; each dip below converts real
            # pairs to complex ones, sweeping the r = 8..20 signatures where
            # most unclaimed pairs live.
            c = floor_c + rng.choice((0, 0, 0, 1, 2, 4, 6, -1, -1, -2, -2, -3, -4, -5))
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

def load_intelligence():
    """Server truth for the targeted gate: the pairs we already hold, the
    pairs nobody holds (a full point each), and the pairs exactly one other
    team holds (a crowding target: about half a point gained and half a
    point taken from the incumbent)."""
    owned, tier0, tier1 = set(), set(), set()

    labels_path = ROOT / "data" / "labels.jsonl"
    if labels_path.exists():
        for raw in labels_path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(raw)
            owned.add((rec["t"], rec["r"]))

    progress_path = ROOT / "data" / "label_progress.json"
    if progress_path.exists():
        for item in json.loads(progress_path.read_text(encoding="utf-8")):
            t = item["t"]
            for sig in item.get("signatures", []):
                pair = (t, sig["r"])
                k = sig.get("teamCount", 0)
                if k == 0:
                    tier0.add(pair)
                elif k == 1 and pair not in owned:
                    tier1.add(pair)

    return owned, tier0, tier1


# Unclaimed-pair density by signature (from the last remaining-pairs pull);
# exploration lines go where the empty territory is largest.
R_WEIGHT = {16: 6, 24: 5, 20: 4, 12: 3, 8: 3, 0: 2, 4: 2,
            6: 1, 14: 1, 18: 1, 10: 1, 2: 1, 22: 1}


def build_batches(n_batches: int):
    seed_ledger_from_submission()
    baseline_fields = load_baseline_fields()
    ledger_fields, ledger_clusters = load_ledger()
    owned, tier0, tier1 = load_intelligence()
    print(f"intelligence: {len(owned)} owned pairs, {len(tier0)} k=0 pairs, "
          f"{len(tier1)} k=1 crowding targets")

    # The predictor only earns its cost and its trust once nearly every
    # group is profiled: at partial coverage the true group is often absent
    # from the candidate set, so a confident match is confidently wrong.
    predictor = None
    profiles = ROOT / "data" / "group_profiles.jsonl"
    profile_count = sum(1 for _ in profiles.open()) if profiles.exists() else 0
    if profile_count >= 24000:
        from predict_label import Predictor
        predictor = Predictor()
        print(f"predictor: {len(predictor.groups)} group profiles loaded, gate ON")
    else:
        print(f"predictor: {profile_count} profiles (< 24000), gate OFF, "
              f"pure construction diversity")

    # Measured target-zone hit rates (t <= 12000, where the unclaimed pairs
    # live): compositum 57 percent, compose 15 percent, tower 1.6 percent.
    # The plan follows the evidence: composita lead, towers are a thin tail
    # kept only for the high-index unclaimed signatures they occasionally
    # reach.
    plan = [
        (engine_composita, 60000),
        (engine_compose, 20000),
        (engine_totally_real, 20000),
        (engine_towers, 30000),
    ]

    hits0 = []             # predicted onto a pair no team holds: 1 point
    hits1 = []             # predicted onto a lone team's pair: crowding
    explore = []           # predictor abstained: could be anything
    picked_clusters = set(ledger_clusters)
    claimed_this_run = set()
    seen_fields = set(baseline_fields) | ledger_fields
    target = n_batches * BATCH_LINES
    started = time.time()
    stats = {"raw": 0, "irreducible": 0, "tier0": 0, "tier1": 0,
             "explore": 0, "skipped_crowded": 0}

    def selected():
        return len(hits0) + len(hits1) + len(explore)

    for engine, count in plan:
        if selected() >= target * 2:
            break
        for coeffs, tag in engine(count):
            stats["raw"] += 1
            if stats["raw"] % 10000 == 0:
                print(f"  raw {stats['raw']}, tier0 {stats['tier0']}, "
                      f"tier1 {stats['tier1']}, explore {stats['explore']}, "
                      f"{time.time() - started:.0f}s", flush=True)
            if selected() >= target * 2:
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

            if predictor is not None:
                label = predictor.confident(coeffs)
                if label is not None:
                    pair = (label, r)
                    if pair in owned or pair in claimed_this_run:
                        continue
                    if pair in tier0:
                        claimed_this_run.add(pair)
                        stats["tier0"] += 1
                        hits0.append((coeffs, f"{tag} t={label}", kh, r))
                    elif pair in tier1:
                        claimed_this_run.add(pair)
                        stats["tier1"] += 1
                        hits1.append((coeffs, f"{tag} t={label}", kh, r))
                    else:
                        # Confidently predicted onto a crowded pair: the
                        # line is worth more spent anywhere else.
                        stats["skipped_crowded"] += 1
                    continue
            stats["explore"] += 1
            explore.append((coeffs, tag, kh, r))

    # Full-point captures lead every batch, crowding attacks follow, and
    # the abstained exploration tail goes where open territory is densest.
    explore.sort(key=lambda item: -R_WEIGHT.get(item[3], 1))
    picked = hits0 + hits1 + explore
    picked = picked[:target]

    BATCH_DIR.mkdir(exist_ok=True)
    # Continue numbering after existing batches; never overwrite history.
    existing = [int(p.stem.split("_")[-1]) for p in BATCH_DIR.glob("igp24_batch_*.txt")]
    next_index = max(existing, default=0) + 1
    written = []
    with LEDGER.open("a", encoding="utf-8") as ledger:
        for b in range(n_batches):
            chunk = picked[b * BATCH_LINES:(b + 1) * BATCH_LINES]
            if not chunk:
                break
            name = f"igp24_batch_{next_index + b:03d}.txt"
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
          f"tier0 {stats['tier0']}, tier1 {stats['tier1']}, "
          f"explore {stats['explore']}, "
          f"skipped crowded {stats['skipped_crowded']}")
    for name, count in written:
        print(f"wrote batches/{name}: {count} lines")
    print(f"total time {time.time() - started:.0f}s")


if __name__ == "__main__":
    n = 10
    if "--batches" in sys.argv:
        n = int(sys.argv[sys.argv.index("--batches") + 1])
    build_batches(n)
