# ==============================================================================
# File: steered.py
# Description: Provenance steered signature attack. data/steered_targets.json
#   lists (label, missing signature) pairs currently held by only one or two
#   teams, together with the degree-12 bases whose relative quadratic
#   extensions produced that label before. This run regenerates candidates
#   from exactly those bases with theta placed at the wanted sign count, so
#   the emitted label mixture is enriched for the target label at the target
#   signature. No local recognition is attempted: the server labels every
#   submission, and the next cycle's progress pull shows which targets were
#   joined. Joining a k=1 pair pays half a point and halves the holder.
# Usage: py scripts/steered.py [per_target]
# Tech Stack: Python 3.10+, python-flint, NumPy
# ==============================================================================

from __future__ import annotations

import json
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


def main(per_target=12):
    targets = json.loads((ROOT / "data" / "steered_targets.json").read_text())
    nf12 = {}
    for raw in (ROOT / "data" / "nf12.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            g = json.loads(raw)
            nf12[g["label"]] = g["fields"]
    seen = set()
    for raw in (ROOT / "data" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            try:
                seen.add(F.canonical(
                    [int(v) for v in json.loads(raw)["coeffs"].split(",")]))
            except Exception:
                pass
    print(f"targets {len(targets)}, ledger {len(seen)}", flush=True)

    # Build Base objects lazily per (12T label, min real embeddings needed).
    cache = {}

    def bases_for(blabel, j):
        key = blabel
        if key not in cache:
            built = []
            for fld in nf12.get(blabel, [])[:10]:
                try:
                    built.append(R.Base(blabel, fld["coeffs"]))
                except Exception:
                    pass
            cache[key] = built
        return [b for b in cache[key] if b.r1 >= j]

    rows = []
    started = time.time()
    made = defaultdict(int)
    for tkey, tv in targets.items():
        t, r, kk = tv["t"], tv["r"], tv["k"]
        j = r // 2
        pool = []
        for blabel in sorted(tv["bases"], key=tv["bases"].get, reverse=True):
            pool.extend(bases_for(blabel, j))
        if not pool:
            continue
        tries = 0
        while made[tkey] < per_target and tries < per_target * 8:
            tries += 1
            base = pool[tries % len(pool)]
            c = R.theta_for_j(base, j)
            if c is None:
                continue
            coeffs = R.minpoly_sqrt(base, c)
            if coeffs is None or max(abs(v) for v in coeffs) > R.MAX_ABS:
                continue
            key = F.canonical(coeffs)
            if key in seen:
                continue
            if not is_irreducible_deg24(coeffs):
                continue
            rr = real_roots(coeffs)
            if rr != r:
                continue
            seen.add(key)
            made[tkey] += 1
            rows.append((coeffs,
                         f"steer t={t} want_r={r} k={kk} base={base.label}"))
        if time.time() - started > 2400:
            print("time budget reached", flush=True)
            break
    hit = sum(1 for v in made.values() if v > 0)
    print(f"generated {len(rows)} candidates covering {hit} targets "
          f"in {int(time.time()-started)}s", flush=True)
    if not rows:
        return
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    idx = max(existing, default=0) + 1
    with (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8") as ledger:
        for start in range(0, len(rows), 1000):
            chunk = rows[start:start + 1000]
            name = f"igp24_batch_{idx:03d}.txt"
            with (OUT / name).open("w", encoding="ascii", newline="\n") as fh:
                fh.write("# IGP24 steered wave: provenance guided signature "
                         "attack on k<=2 pairs.\n")
                for coeffs, tag in chunk:
                    fh.write(",".join(map(str, coeffs)) + f" # {tag}\n")
            for coeffs, tag in chunk:
                ledger.write(json.dumps({
                    "coeffs": ",".join(map(str, coeffs)), "key": "",
                    "r": real_roots(coeffs), "batch": name}) + "\n")
            print(f"wrote batches/{name}: {len(chunk)}", flush=True)
            idx += 1


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
