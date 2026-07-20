# ==============================================================================
# File: group_profiles.py
# Description: Turns each transitive group's generators into a cycle-type
#   profile: the set of cycle types its elements exhibit, with sampled
#   densities. By Chebotarev, a polynomial's Frobenius cycle types at random
#   primes are drawn from exactly this distribution, so the profiles are the
#   reference book that lets predict_label.py name a candidate's Galois group
#   without Magma. Sampling uses product replacement, which walks huge groups
#   as easily as small ones.
# Usage: py scripts/group_profiles.py
# Tech Stack: Python 3.10+
# ==============================================================================

from __future__ import annotations

import json
import random
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ROOT / "data" / "groups24.jsonl"
OUT = ROOT / "data" / "group_profiles.jsonl"

N = 24
SAMPLES = 3000
SLOTS = 8          # product replacement slots
BURN = 60          # replacement steps before sampling starts

rng = random.Random(24024)


def cycles_to_perm(gen):
    """LMFDB stores a generator as a list of cycles over 1..24; turn it into
    a 0-based mapping tuple."""
    perm = list(range(N))
    for cycle in gen:
        for i, a in enumerate(cycle):
            b = cycle[(i + 1) % len(cycle)]
            perm[a - 1] = b - 1
    return tuple(perm)


def compose(p, q):
    """p after q."""
    return tuple(p[q[i]] for i in range(N))


def cycle_type(p):
    seen = [False] * N
    lens = []
    for i in range(N):
        if seen[i]:
            continue
        length = 0
        j = i
        while not seen[j]:
            seen[j] = True
            j = p[j]
            length += 1
        lens.append(length)
    return tuple(sorted(lens))


def profile(gens):
    """Sampled cycle-type distribution via product replacement: keep a pool
    of group elements, repeatedly replace one slot with its product with
    another, and read cycle types off the walk."""
    pool = [cycles_to_perm(g) for g in gens]
    while len(pool) < SLOTS:
        pool.append(pool[rng.randrange(len(pool))])

    for _ in range(BURN):
        i, j = rng.randrange(SLOTS), rng.randrange(SLOTS)
        if i != j:
            pool[i] = compose(pool[i], pool[j])

    counts = {}
    for _ in range(SAMPLES):
        i, j = rng.randrange(SLOTS), rng.randrange(SLOTS)
        if i != j:
            pool[i] = compose(pool[i], pool[j])
        ct = cycle_type(pool[i])
        counts[ct] = counts.get(ct, 0) + 1
    return counts


def main():
    done = set()
    if OUT.exists():
        for raw in OUT.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                done.add(json.loads(raw)["t"])
    print(f"already profiled {len(done)}")

    started = time.time()
    handled = 0
    with OUT.open("a", encoding="utf-8") as fh:
        for raw in GROUPS.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            rec = json.loads(raw)
            if rec["t"] in done:
                continue
            try:
                counts = profile(rec["gens"])
            except Exception:
                continue
            fh.write(json.dumps({
                "t": rec["t"],
                "types": {",".join(map(str, k)): v for k, v in counts.items()},
            }) + "\n")
            handled += 1
            if handled % 1000 == 0:
                fh.flush()
                print(f"profiled {handled}, {time.time() - started:.0f}s",
                      flush=True)

    print(f"done: {handled} new profiles, {time.time() - started:.0f}s total")


if __name__ == "__main__":
    main()
