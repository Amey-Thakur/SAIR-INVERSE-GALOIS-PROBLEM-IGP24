# ==============================================================================
# File: microtarget.py
# Description: The one positive-value target left after the ceiling analysis.
#   Of the unclaimed mid-index pairs, all but 87 sit on groups our
#   constructions cannot reach; those 87 sit on 45 groups we DO reach, but at
#   real-root signatures we have never produced (mostly r = 8, 12, 16, 24).
#   This generator draws high-real-root fields, fingerprints each by its
#   Frobenius cycle types, and keeps only the ones whose fingerprint matches
#   a target group at a signature that group still needs. Ground truth is our
#   own labeled data, so it needs no group download.
# Usage: py scripts/microtarget.py
# Tech Stack: Python 3.10+, python-flint, SymPy, NumPy
# ==============================================================================

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factory as F
from fingerprint import group_key, is_irreducible_deg24, real_roots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "batches"


def main(budget_s=2400):
    targets = {k: set(v) for k, v in
               json.loads((ROOT / "data" / "microtargets.json").read_text()).items()}
    needed_r = set().union(*targets.values())
    print(f"targets: {len(targets)} fingerprints, needed signatures {sorted(needed_r)}")

    baseline = set()
    for row in csv.DictReader((ROOT / "data" / "lmfdb_baseline.csv").open(encoding="utf-8")):
        c = tuple(int(v) for v in row["coeffs"].split(","))
        baseline.add(c)
        baseline.add(tuple(v * (-1) ** i for i, v in enumerate(c)))
    seen = set()
    for raw in (ROOT / "data" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            c = [int(v) for v in json.loads(raw)["coeffs"].split(",")]
            seen.add(F.canonical(c))

    # High-real-root sources: the totally real family sweeps r = 8..24, and
    # real-shifted composita add coverage. Only the needed signatures survive.
    hits = []
    hit_pairs = set()
    started = time.time()
    checked = 0

    def consider(coeffs):
        nonlocal checked
        if coeffs is None or len(coeffs) != 25 or coeffs[24] != 1 or coeffs[0] == 0:
            return
        key = F.canonical(coeffs)
        if key in seen or tuple(coeffs) in baseline:
            return
        r = real_roots(coeffs)
        if r not in needed_r:
            return
        checked += 1
        if not is_irreducible_deg24(coeffs):
            return
        seen.add(key)
        kh = F.key_hash(group_key(coeffs))
        if kh in targets and r in targets[kh] and (kh, r) not in hit_pairs:
            hit_pairs.add((kh, r))
            hits.append((coeffs, f"micro t_fp={kh[:8]} r={r}"))

    while time.time() - started < budget_s:
        for coeffs, _ in F.engine_totally_real(400):
            consider(coeffs)
            if time.time() - started >= budget_s:
                break
        for coeffs, _ in F.engine_composita(200):
            consider(coeffs)
            if time.time() - started >= budget_s:
                break
        print(f"  {int(time.time()-started)}s: irreducible-checked {checked}, "
              f"target hits {len(hits)}", flush=True)
        if len(hits) >= 300:
            break

    if not hits:
        print("no target hits found this run")
        return
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    name = f"igp24_micro_{max(existing, default=0) + 1:03d}.txt"
    path = OUT / name
    with path.open("w", encoding="ascii", newline="\n") as fh:
        fh.write("# IGP24 micro-target wave: reachable groups at unclaimed "
                 "signatures.\n")
        for coeffs, tag in hits:
            fh.write(",".join(map(str, coeffs)) + f" # {tag}\n")
    ledger = (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8")
    for coeffs, tag in hits:
        ledger.write(json.dumps({
            "coeffs": ",".join(map(str, coeffs)),
            "key": F.key_hash(group_key(coeffs)),
            "r": real_roots(coeffs), "batch": name,
        }) + "\n")
    ledger.close()
    print(f"wrote batches/{name}: {len(hits)} target-matched polynomials")


if __name__ == "__main__":
    main()
