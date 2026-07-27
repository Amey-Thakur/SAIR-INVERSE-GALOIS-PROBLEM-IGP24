# ==============================================================================
# File: block_targets.py
# Description: Structural steering by imprimitivity. For every thin target
#   label (some signature held by at most two teams) whose permutation
#   generators are on disk, this detects a block system of twelve size-2
#   blocks by union-find closure, computes the induced degree-12 action, and
#   identifies its 12T class by matching sampled cycle-type distributions
#   against all 301 degree-12 transitive groups. A label with block quotient
#   Q is a subgroup of C2 wr Q, which is exactly what a relative quadratic
#   extension over a base field with group Q produces, so candidates are then
#   generated from nf12 fields of Q at the thin signatures. This replaces
#   empirical provenance with the group theoretic ground truth.
# Usage: py scripts/block_targets.py [per_target]
# Tech Stack: Python 3.10+, python-flint, NumPy
# ==============================================================================

from __future__ import annotations

import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factory as F
import relative as R
from fingerprint import is_irreducible_deg24, real_roots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "batches"
rng = random.Random(1729)


def cycles_to_perm(gen, n):
    perm = list(range(n))
    for cycle in gen:
        for i, a in enumerate(cycle):
            perm[a - 1] = cycle[(i + 1) % len(cycle)] - 1
    return tuple(perm)


def compose(p, q):
    return tuple(p[q[i]] for i in range(len(p)))


def cycle_type(p):
    n = len(p)
    seen = [False] * n
    lens = []
    for i in range(n):
        if seen[i]:
            continue
        j, length = i, 0
        while not seen[j]:
            seen[j] = True
            j = p[j]
            length += 1
        lens.append(length)
    return tuple(sorted(lens))


def sample_profile(perms, samples=2500, slots=8, burn=60):
    pool = list(perms)
    while len(pool) < slots:
        pool.append(pool[rng.randrange(len(pool))])
    for _ in range(burn):
        i, j = rng.randrange(slots), rng.randrange(slots)
        if i != j:
            pool[i] = compose(pool[i], pool[j])
    counts = defaultdict(int)
    for _ in range(samples):
        i, j = rng.randrange(slots), rng.randrange(slots)
        if i != j:
            pool[i] = compose(pool[i], pool[j])
        counts[cycle_type(pool[i])] += 1
    total = sum(counts.values())
    return {ct: c / total for ct, c in counts.items()}


def block_system(perms):
    """Find a G-invariant partition of 0..23 into 12 pairs, if one exists."""
    for j in range(1, 24):
        parent = list(range(24))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        union(0, j)
        changed = True
        while changed:
            changed = False
            for p in perms:
                for x in range(24):
                    rx = find(x)
                    px, prx = find(p[x]), find(p[rx])
                    if px != prx:
                        union(p[x], p[rx])
                        changed = True
        blocks = defaultdict(list)
        for x in range(24):
            blocks[find(x)].append(x)
        sizes = sorted(len(b) for b in blocks.values())
        if sizes == [2] * 12:
            blist = sorted(blocks.values())
            index = {}
            for bi, b in enumerate(blist):
                for x in b:
                    index[x] = bi
            action = [tuple(index[p[blist[bi][0]]] for bi in range(12))
                      for p in perms]
            return action
    return None


def dist(a, b):
    keys = set(a) | set(b)
    return sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)


def main(per_target=15):
    k = {}
    for it in json.loads((ROOT / "data" / "label_progress.json").read_text(encoding="utf-8")):
        for s in it["signatures"]:
            k[(it["t"], s["r"])] = s["teamCount"]
    gens24 = {}
    for raw in (ROOT / "data" / "groups24.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rec = json.loads(raw)
            gens24[rec["t"]] = rec["gens"]
    ourt = defaultdict(set)
    for raw in (ROOT / "data" / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(raw)
        ourt[rec["t"]].add(rec["r"])
    # thin targets: signature with k <= 2 that we do not hold, gens on disk
    thin = defaultdict(list)
    for (t, r), kk in k.items():
        if kk <= 2 and t in gens24 and r not in ourt.get(t, set()):
            thin[t].append((r, kk))
    print(f"thin labels with gens: {len(thin)}", flush=True)

    # 12T reference profiles
    ref = {}
    for raw in (ROOT / "data" / "groups12.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(raw)
        perms = [cycles_to_perm(g, 12) for g in rec["gens"]]
        ref[rec["label"]] = sample_profile(perms)
    print(f"12T reference profiles: {len(ref)}", flush=True)

    # identify block quotients
    matches = {}
    started = time.time()
    for t in sorted(thin):
        perms = [cycles_to_perm(g, 24) for g in gens24[t]]
        action = block_system(perms)
        if action is None:
            continue
        prof = sample_profile(action)
        scored = sorted(((dist(prof, rp), lab) for lab, rp in ref.items()))
        matches[t] = [lab for _, lab in scored[:2]]
        if time.time() - started > 900:
            break
    print(f"block quotients identified: {len(matches)} "
          f"({int(time.time()-started)}s)", flush=True)
    json.dump({str(t): {"quotients": q, "needs": thin[t]}
               for t, q in matches.items()},
              (ROOT / "data" / "block_targets.json").open("w"), indent=0)

    # generate candidates over the matched bases
    nf12 = {}
    for raw in (ROOT / "data" / "nf12.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            g = json.loads(raw)
            nf12[g["label"]] = g["fields"]
    cache = {}

    def bases_for(blabel, j):
        if blabel not in cache:
            built = []
            for fld in nf12.get(blabel, [])[:10]:
                try:
                    built.append(R.Base(blabel, fld["coeffs"]))
                except Exception:
                    pass
            cache[blabel] = built
        return [b for b in cache[blabel] if b.r1 >= j]

    seen = set()
    for raw in (ROOT / "data" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            try:
                seen.add(F.canonical(
                    [int(v) for v in json.loads(raw)["coeffs"].split(",")]))
            except Exception:
                pass
    rows = []
    for t, quots in matches.items():
        for r, kk in thin[t]:
            j = r // 2
            pool = []
            for q in quots:
                pool.extend(bases_for(q, j))
            if not pool:
                continue
            got, tries = 0, 0
            while got < per_target and tries < per_target * 8:
                tries += 1
                base = pool[tries % len(pool)]
                c = R.theta_for_j(base, j)
                if c is None:
                    continue
                coeffs = R.minpoly_sqrt(base, c)
                if coeffs is None or max(abs(v) for v in coeffs) > R.MAX_ABS:
                    continue
                key = F.canonical(coeffs)
                if key in seen or not is_irreducible_deg24(coeffs):
                    continue
                if real_roots(coeffs) != r:
                    continue
                seen.add(key)
                got += 1
                rows.append((coeffs, f"block t={t} q={base.label} r={r} k={kk}"))
    print(f"generated {len(rows)} block-steered candidates", flush=True)
    if not rows:
        return
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    idx = max(existing, default=0) + 1
    with (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8") as ledger:
        for start in range(0, len(rows), 1000):
            chunk = rows[start:start + 1000]
            name = f"igp24_batch_{idx:03d}.txt"
            with (OUT / name).open("w", encoding="ascii", newline="\n") as fh:
                fh.write("# IGP24 block wave: imprimitivity quotient steering "
                         "of thin pairs.\n")
                for coeffs, tag in chunk:
                    fh.write(",".join(map(str, coeffs)) + f" # {tag}\n")
            for coeffs, tag in chunk:
                ledger.write(json.dumps({
                    "coeffs": ",".join(map(str, coeffs)), "key": "",
                    "r": real_roots(coeffs), "batch": name}) + "\n")
            print(f"wrote batches/{name}: {len(chunk)}", flush=True)
            idx += 1


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 15)
