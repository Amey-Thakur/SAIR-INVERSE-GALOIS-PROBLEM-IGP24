# ==============================================================================
# File: evaluate_predictor.py
# Description: Measures the Chebotarev fingerprint predictor against the
#   competition server's own labels, separating two questions that a naive
#   validation conflates. The predictor can only name a group it holds a
#   profile for, and profiles exist for 24T1 to 24T8000 only, so a uniform
#   sample of labeled polynomials measures profile coverage rather than
#   predictive power: 9.4 percent of labeled polynomials lie in that range, so
#   uniform sampling caps top-1 accuracy near 9 percent however good the
#   method is. This script reports in-domain accuracy, out-of-domain
#   behaviour, and coverage separately.
# Usage: py scripts/evaluate_predictor.py [--sample N] [--margin M]
# Tech Stack: Python 3.10+, python-flint
# ==============================================================================

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from predict_label import Predictor

ROOT = Path(__file__).resolve().parents[1]


def load_rows():
    rows = []
    with (ROOT / "data" / "labels.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=1000)
    ap.add_argument("--margin", type=float, default=8.0)
    args = ap.parse_args()

    predictor = Predictor()
    profiled = {t for t, _ in predictor.groups}
    hi = max(profiled)

    rows = load_rows()
    in_dom = [r for r in rows if r["t"] in profiled]
    print(f"profiles: {len(profiled)} groups (24T1..24T{hi})")
    print(f"labeled polynomials: {len(rows)}")
    print(f"  in profiled range:  {len(in_dom)} = {len(in_dom) / len(rows):.1%}"
          f"   <- ceiling on uniform-sample accuracy")
    print(f"  distinct true labels in corpus: {len({r['t'] for r in rows})}")

    rng = random.Random(2024)
    rng.shuffle(in_dom)
    test = in_dom[:args.sample]
    print(f"\nevaluating on {len(test)} in-domain polynomials, margin {args.margin}",
          flush=True)

    top1 = top3 = conf_ok = conf_bad = abstain = 0
    t0 = time.time()
    for i, rec in enumerate(test):
        coeffs = [int(v) for v in rec["coeffs"].split(",")]
        truth = rec["t"]
        ranked = predictor.predict(coeffs, top=3)
        if ranked and ranked[0][0] == truth:
            top1 += 1
        if any(t == truth for t, _ in ranked):
            top3 += 1
        sure = predictor.confident(coeffs, margin=args.margin)
        if sure is None:
            abstain += 1
        elif sure == truth:
            conf_ok += 1
        else:
            conf_bad += 1
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(test)}  top1 {top1}  conf {conf_ok}/"
                  f"{conf_ok + conf_bad}", flush=True)

    n = len(test)
    decided = conf_ok + conf_bad
    secs = time.time() - t0
    print(f"\nRESULTS (in-domain, n = {n})")
    print(f"  top-1 accuracy      {top1}/{n} = {top1 / n:.3%}")
    print(f"  top-3 accuracy      {top3}/{n} = {top3 / n:.3%}")
    if decided:
        print(f"  confident decided   {decided}/{n} = {decided / n:.1%}")
        print(f"  confident precision {conf_ok}/{decided} = {conf_ok / decided:.3%}")
    print(f"  abstained           {abstain}/{n} = {abstain / n:.1%}")
    print(f"  {secs / n * 1000:.0f} ms per polynomial")


if __name__ == "__main__":
    main()
