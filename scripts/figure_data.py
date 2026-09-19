# ==============================================================================
# File: figure_data.py
# Description: Data for the paper's explanatory figures, which the analysis
#   script does not produce because they illustrate rather than measure.
#   Three things. (1) The distribution of rho*, the Bhattacharyya coefficient
#   between each group and its nearest competitor, which shows how crowded the
#   candidate set is. (2) A worked example: one polynomial, the cycle types it
#   produces at the first primes, and the candidates those observations
#   promote, so a reader can follow the method on a concrete case rather than
#   only in the abstract. (3) Two confusable groups' cycle-type distributions
#   side by side, which makes a coefficient near 1 tangible.
# Usage: py scripts/figure_data.py [--out data/figure_data.json]
# Tech Stack: Python 3.10+, python-flint, numpy
# ==============================================================================

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis import ProfileMatrix, bhattacharyya_nearest, observe
from predict_label import PRED_PRIMES

ROOT = Path(__file__).resolve().parents[1]


def rho_histogram(best, edges):
    """How many groups fall in each band of nearest-competitor distance."""
    counts, _ = np.histogram(best, bins=edges)
    return [{"lo": float(a), "hi": float(b), "count": int(c)}
            for a, b, c in zip(edges, edges[1:], counts)]


def worked_example(pm, rows, want_correct=True, want_confident=True, margin=8.0):
    """One polynomial carried through the method, start to finish."""
    pos = {int(t): i for i, t in enumerate(pm.t)}
    for rec in rows:
        coeffs = [int(v) for v in rec["coeffs"].split(",")]
        truth = rec["t"]
        obs = observe(coeffs)
        cols = pm.columns(obs)
        if not cols:
            continue
        score = pm.logp[:, cols].sum(axis=1)
        order = np.argsort(-score, kind="stable")
        pred = int(pm.t[order[0]])
        gap = float(score[order[0]] - score[order[1]])
        if (pred == truth) != want_correct:
            continue
        if (gap >= margin) != want_confident:
            continue
        rival = int(pm.t[order[1]])
        return {
            "coeffs": rec["coeffs"],
            "truth": truth,
            "predicted": pred,
            "margin": gap,
            "confident": gap >= margin,
            "field_disc_digits": len(rec.get("fieldDiscAbs", "")),
            # the first observations, as a reader would follow them
            "observations": [
                {"prime": p, "cycle_type": list(t) if t else None}
                for p, t in zip(PRED_PRIMES[:10], obs[:10])
            ],
            "top3": [{"t": int(pm.t[i]), "loglik": float(score[i])}
                     for i in order[:3]],
            "rho_to_rival": float(pm.sqrtp[pos[truth]] @ pm.sqrtp[pos[rival]]),
        }
    return None


def confusable_pair(pm, best, who, target=0.99):
    """A pair of groups close enough to be hard, with the cycle types that
    separate them and the many more that do not."""
    # a pair near the target coefficient, so the illustration is typical
    # rather than extreme
    i = int(np.argmin(np.abs(best - target)))
    j = int(who[i])
    inv = {v: k for k, v in pm.index.items()}
    rows = []
    for c in range(pm.prob.shape[1]):
        a, b = float(pm.prob[i, c]), float(pm.prob[j, c])
        if a or b:
            rows.append({"cycle_type": list(inv[c]), "p": a, "q": b,
                         "contribution": (a * b) ** 0.5})
    rows.sort(key=lambda r: -r["contribution"])
    return {
        "group_a": int(pm.t[i]),
        "group_b": int(pm.t[j]),
        "rho": float(best[i]),
        "shared_types": len(rows),
        "rows": rows[:8],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "figure_data.json"))
    ap.add_argument("--sample", type=int, default=600)
    args = ap.parse_args()

    print("loading profiles", flush=True)
    pm = ProfileMatrix()
    best, who = bhattacharyya_nearest(pm)

    edges = [0.0, 0.90, 0.95, 0.97, 0.98, 0.99, 0.995, 0.999, 1.0]
    hist = rho_histogram(best, edges)
    print("rho* distribution")
    for h in hist:
        print(f"  {h['lo']:.3f}-{h['hi']:.3f}  {h['count']:5d}"
              f"  {h['count'] / len(pm):6.1%}")

    print("\nloading labels", flush=True)
    rows = [json.loads(l) for l
            in (ROOT / "data" / "labels.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    profiled = set(int(t) for t in pm.t)
    in_dom = [r for r in rows if r["t"] in profiled]
    rng = random.Random(2024)
    rng.shuffle(in_dom)
    test = in_dom[:args.sample]

    print("worked example", flush=True)
    ex = worked_example(pm, test)
    if ex:
        print(f"  truth 24T{ex['truth']}, predicted 24T{ex['predicted']}, "
              f"margin {ex['margin']:.1f}")
        for o in ex["observations"][:5]:
            print(f"    p={o['prime']}  {o['cycle_type']}")
        for c in ex["top3"]:
            print(f"    24T{c['t']}  loglik {c['loglik']:.1f}")

    print("\nconfusable pair", flush=True)
    pair = confusable_pair(pm, best, who)
    print(f"  24T{pair['group_a']} vs 24T{pair['group_b']}, "
          f"rho {pair['rho']:.4f}, {pair['shared_types']} types with mass")
    for r in pair["rows"][:5]:
        print(f"    {r['cycle_type']}  p={r['p']:.4f}  q={r['q']:.4f}")

    out = {
        "groups": len(pm),
        "rho_histogram": hist,
        "worked_example": ex,
        "confusable_pair": pair,
    }
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
