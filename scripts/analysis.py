# ==============================================================================
# File: analysis.py
# Description: The experiments behind the paper's analysis sections. Three
#   questions the headline accuracy figure does not answer. (1) How many primes
#   does the classifier actually need? Factorisation dominates its cost, so the
#   prime count is the one tuning knob that matters; the ablation here varies it
#   with everything else held fixed. (2) Which group pairs can be separated at
#   all? The Bhattacharyya coefficient between two cycle-type distributions
#   bounds the error of any test that distinguishes them, so it predicts, before
#   any polynomial is factored, how many primes a pair demands. (3) Do the
#   classifier's mistakes fall where that bound says they must? The error
#   analysis pairs each wrong answer with the coefficient between the true and
#   predicted profiles.
#   Scoring is vectorised over groups so the ablation costs one factorisation
#   pass rather than one per prime count. The vectorised scorer is checked
#   against predict_label.Predictor before it is used.
# Usage: py scripts/analysis.py [--sample N] [--margin M] [--out results.json]
# Tech Stack: Python 3.10+, python-flint, numpy
# ==============================================================================

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import cycle_pattern
from predict_label import PRED_PRIMES, Predictor

ROOT = Path(__file__).resolve().parents[1]
FLOOR = math.log(1e-4)          # the penalty predict_label applies to an unseen type
PRIME_STEPS = [5, 10, 15, 20, 30, 40, 50, 60]


# ----------------------------------------------------------------------------
# profiles as matrices
# ----------------------------------------------------------------------------

class ProfileMatrix:
    """The group profiles as arrays, with the type keys shared across groups.

    Holds three things: `logp`, the log-probability of each type under each
    group with the same floor predict_label uses, for classification; `sqrtp`,
    the square roots of those probabilities, for Bhattacharyya coefficients;
    and `counts`, the raw sample sizes, because a profile is an estimate and
    its precision depends on how many group elements were drawn.
    """

    def __init__(self, path=ROOT / "data" / "group_profiles.jsonl"):
        raw = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        types = sorted({k for rec in raw for k in rec["types"]})
        col = {k: j for j, k in enumerate(types)}
        self.index = {tuple(int(x) for x in k.split(",")): j for k, j in col.items()}
        self.t = np.array([rec["t"] for rec in raw], dtype=np.int32)

        g, n = len(raw), len(types)
        prob = np.zeros((g, n), dtype=np.float64)
        self.counts = np.zeros(g, dtype=np.int64)
        for i, rec in enumerate(raw):
            total = sum(rec["types"].values())
            self.counts[i] = total
            for key, c in rec["types"].items():
                prob[i, col[key]] = c / total

        self.prob = prob
        self.logp = np.where(prob > 0, np.log(np.maximum(prob, 1e-300)), FLOOR)
        self.sqrtp = np.sqrt(prob).astype(np.float32)

    def __len__(self):
        return len(self.t)

    def columns(self, patterns):
        """Column index of each observed cycle type, dropping any type that no
        profile contains. Such a type costs every group the same floor, so it
        cannot change the ranking and dropping it is exact, not an
        approximation."""
        return [self.index[p] for p in patterns if p is not None and p in self.index]


def observe(coeffs, primes=PRED_PRIMES):
    """Cycle types of the polynomial at each prime, in prime order.

    One entry per prime, None where the prime is ramified and carries no
    evidence. Keeping the None rather than dropping it matters for the
    ablation: the budget being varied is primes tried, which the caller pays
    for whether or not the prime turns out to be usable.
    """
    return [cycle_pattern(coeffs, p) for p in primes]


# ----------------------------------------------------------------------------
# agreement with the released predictor
# ----------------------------------------------------------------------------

def check_against_predictor(pm, rows, n=25):
    """The vectorised scorer must rank exactly as predict_label does, or the
    ablation measures a different classifier from the one the paper reports."""
    ref = Predictor()
    bad = 0
    for rec in rows[:n]:
        coeffs = [int(v) for v in rec["coeffs"].split(",")]
        obs = observe(coeffs)
        cols = pm.columns(obs)
        score = pm.logp[:, cols].sum(axis=1)
        mine = [int(pm.t[i]) for i in np.argsort(-score, kind="stable")[:3]]
        theirs = [t for t, _ in ref.predict(coeffs, top=3)]
        if mine[0] != theirs[0]:
            bad += 1
    return bad


# ----------------------------------------------------------------------------
# experiment 1: how many primes are needed
# ----------------------------------------------------------------------------

def ablation(pm, rows, margin, steps=PRIME_STEPS):
    """Top-1, top-3, abstention and confident precision at each prime count.

    One factorisation pass serves every step: the log-likelihood is a sum over
    observations, so scores at m primes are a prefix sum of scores at 60.
    """
    tally = {m: dict(top1=0, top3=0, ok=0, bad=0, abstain=0) for m in steps}
    fact_s = score_s = 0.0

    for rec in rows:
        coeffs = [int(v) for v in rec["coeffs"].split(",")]
        truth = rec["t"]

        t0 = time.perf_counter()
        obs = observe(coeffs)
        fact_s += time.perf_counter() - t0

        t0 = time.perf_counter()
        score = np.zeros(len(pm), dtype=np.float64)
        # k counts primes tried, not usable observations, so every polynomial
        # reaches every step: a ramified prime spends budget and returns nothing
        for k, pat in enumerate(obs, 1):
            j = pm.index.get(pat) if pat is not None else None
            if j is not None:
                score += pm.logp[:, j]
            if k in tally:
                rank = np.argsort(-score, kind="stable")[:3]
                cand = [int(pm.t[i]) for i in rank]
                row = tally[k]
                row["top1"] += cand[0] == truth
                row["top3"] += truth in cand
                gap = score[rank[0]] - score[rank[1]]
                if gap < margin:
                    row["abstain"] += 1
                elif cand[0] == truth:
                    row["ok"] += 1
                else:
                    row["bad"] += 1
        score_s += time.perf_counter() - t0

    n = len(rows)
    out = []
    for m in steps:
        r = tally[m]
        decided = r["ok"] + r["bad"]
        out.append(dict(
            primes=m, n=n,
            top1=r["top1"] / n, top3=r["top3"] / n,
            coverage=decided / n,
            precision=(r["ok"] / decided) if decided else None,
            conf_right=r["ok"], conf_wrong=r["bad"],
        ))
    return out, dict(factor_ms=fact_s / n * 1000, score_ms=score_s / n * 1000)


# ----------------------------------------------------------------------------
# experiment 2: which pairs are separable at all
# ----------------------------------------------------------------------------

def bhattacharyya_nearest(pm, chunk=500):
    """For each group, the largest Bhattacharyya coefficient against any other
    group, and which group attains it.

    For distributions p and q the coefficient is rho = sum_lambda sqrt(p q).
    Under equal priors the error of the optimal test on m independent samples
    obeys P_e <= rho^m / 2, so rho fixes how many samples a pair demands: the
    closer to 1, the more primes. The largest coefficient a group faces is
    therefore what governs whether the classifier can name it at all.
    """
    S = pm.sqrtp
    g = len(pm)
    best = np.zeros(g, dtype=np.float32)
    who = np.zeros(g, dtype=np.int32)
    for a in range(0, g, chunk):
        b = min(a + chunk, g)
        block = S[a:b] @ S.T                   # rho for every pair in the block
        for i in range(b - a):
            block[i, a + i] = -1.0             # a group is not its own competitor
        j = np.argmax(block, axis=1)
        best[a:b] = block[np.arange(b - a), j]
        who[a:b] = j
    return best, who


def primes_needed(rho, delta):
    """Primes the Bhattacharyya bound demands to push pairwise error below
    delta. Infinite when the profiles are indistinguishable (rho = 1).

    This is the sufficiency direction. It says when success is guaranteed; it
    never says failure is guaranteed, so a group the bound does not cover may
    still be classified correctly.
    """
    rho = np.clip(rho, 0.0, 1.0 - 1e-12)
    with np.errstate(divide="ignore"):
        m = np.log(2.0 * delta) / np.log(rho)
    return np.where(rho >= 1.0 - 1e-12, np.inf, np.maximum(m, 0.0))


def forced_error(rho, m):
    """Error that no rule can avoid at m primes: (1 - sqrt(1 - rho^(2m))) / 2.

    The necessity direction, and the one that carries the negative result. A
    group whose nearest competitor sits at rho cannot be named more reliably
    than this however the evidence is weighed.
    """
    r2m = np.power(np.clip(rho, 0.0, 1.0), 2 * m)
    return 0.5 * (1.0 - np.sqrt(np.maximum(0.0, 1.0 - r2m)))


# ----------------------------------------------------------------------------
# experiment 3: do the errors fall where the bound says
# ----------------------------------------------------------------------------

def error_analysis(pm, rows, margin, rho_star):
    """Pair every prediction with the coefficient between the true group and
    its strongest rival: the highest-ranked group that is not the true one.

    Comparing the true group against the *predicted* group would be vacuous,
    because a correct prediction names the true group and scores rho = 1 by
    definition. The rival is the group the classifier had to beat, which is
    defined the same way whether or not it won, so correct and incorrect cases
    are measured on the same quantity.

    The theory predicts errors concentrate where the rival is close. If the two
    distributions of rho coincided, the explanation would be wrong.
    """
    pos = {int(t): i for i, t in enumerate(pm.t)}
    right, wrong, ranks, conf_wrong = [], [], [], 0
    per_poly = []          # (rho_star of true group, correct?) for bucketing

    for rec in rows:
        coeffs = [int(v) for v in rec["coeffs"].split(",")]
        truth = rec["t"]
        cols = pm.columns(observe(coeffs))
        if not cols:
            continue
        score = pm.logp[:, cols].sum(axis=1)
        order = np.argsort(-score, kind="stable")
        pred = int(pm.t[order[0]])
        rival = pred if pred != truth else int(pm.t[order[1]])
        rho = float(pm.sqrtp[pos[truth]] @ pm.sqrtp[pos[rival]])
        ok = pred == truth
        (right if ok else wrong).append(rho)
        if not ok:
            ranks.append(int(np.where(pm.t[order] == truth)[0][0]) + 1)
            if score[order[0]] - score[order[1]] >= margin:
                conf_wrong += 1
        per_poly.append((float(rho_star[pos[truth]]), ok))
    return right, wrong, ranks, conf_wrong, per_poly


def accuracy_by_separability(per_poly, edges=(0.0, 0.95, 0.99, 0.999, 1.01)):
    """Accuracy against how crowded the true group's neighbourhood is.

    Buckets each polynomial by rho*, the coefficient between its true group and
    that group's nearest competitor anywhere in the profile set. This is fixed
    before any polynomial is seen, so it is a genuine prediction rather than a
    description of the outcome.
    """
    out = []
    for lo, hi in zip(edges, edges[1:]):
        sel = [ok for r, ok in per_poly if lo <= r < hi]
        if sel:
            out.append(dict(lo=lo, hi=min(hi, 1.0), n=len(sel),
                            acc=sum(sel) / len(sel),
                            bound=float(forced_error(np.array([(lo + min(hi, 1.0)) / 2]), 60)[0])))
    return out


def pct(xs, q):
    return float(np.percentile(xs, q)) if len(xs) else None


# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=600)
    ap.add_argument("--margin", type=float, default=8.0)
    ap.add_argument("--out", default=str(ROOT / "data" / "analysis_results.json"))
    args = ap.parse_args()

    print("loading profiles", flush=True)
    pm = ProfileMatrix()
    print(f"  {len(pm)} groups, {len(pm.index)} distinct cycle types")
    print(f"  profile sample size: min {pm.counts.min()}, median "
          f"{int(np.median(pm.counts))}, max {pm.counts.max()}")

    print("loading labels", flush=True)
    rows = [json.loads(l) for l
            in (ROOT / "data" / "labels.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    profiled = set(int(t) for t in pm.t)
    in_dom = [r for r in rows if r["t"] in profiled]
    print(f"  {len(rows)} labelled, {len(in_dom)} in domain = {len(in_dom)/len(rows):.1%}")

    # the paper's sample, reproduced exactly: same seed, same shuffle, same slice
    rng = random.Random(2024)
    rng.shuffle(in_dom)
    test = in_dom[:args.sample]

    print("checking the vectorised scorer against predict_label", flush=True)
    bad = check_against_predictor(pm, test)
    print(f"  top-1 disagreements on 25 polynomials: {bad}")
    if bad:
        sys.exit("vectorised scorer does not reproduce the released predictor")

    print(f"\nexperiment 1: prime-count ablation on {len(test)} polynomials", flush=True)
    abl, timing = ablation(pm, test, args.margin)
    print(f"  {timing['factor_ms']:.0f} ms factorising + {timing['score_ms']:.0f} ms scoring "
          f"per polynomial")
    print(f"  {'primes':>6} {'top-1':>8} {'top-3':>8} {'cover':>8} {'prec':>8}")
    for r in abl:
        p = f"{r['precision']:.1%}" if r["precision"] is not None else "n/a"
        print(f"  {r['primes']:>6} {r['top1']:>8.1%} {r['top3']:>8.1%} "
              f"{r['coverage']:>8.1%} {p:>8}")

    print("\nexperiment 2: pairwise separability", flush=True)
    best, who = bhattacharyya_nearest(pm)
    print(f"  nearest-competitor rho: median {np.median(best):.4f}, "
          f"90th pct {np.percentile(best, 90):.4f}, max {best.max():.4f}")
    for delta in (0.05, 0.05 / (len(pm) - 1)):
        need = primes_needed(best, delta)
        finite = np.isfinite(need)
        print(f"  sufficiency, delta {delta:.2e}: median primes needed "
              f"{np.median(need[finite]):.0f}; 60 primes guarantee "
              f"{np.mean(need <= 60):.1%} of groups")
    fe = forced_error(best, 60)
    print(f"  necessity at 60 primes: mean forced error {fe.mean():.1%}, "
          f"median {np.median(fe):.1%}")
    for thr in (0.10, 0.25, 0.40):
        print(f"    forced error above {thr:.0%}: {np.mean(fe > thr):.1%} of groups")

    print("\nexperiment 3: error analysis", flush=True)
    right, wrong, ranks, cwr, per_poly = error_analysis(pm, test, args.margin, best)
    print(f"  rho to strongest rival, correct   n={len(right):4d}: "
          f"median {pct(right, 50):.4f}")
    print(f"  rho to strongest rival, incorrect n={len(wrong):4d}: "
          f"median {pct(wrong, 50):.4f}")
    if ranks:
        print(f"  true label's rank when wrong: median {int(np.median(ranks))}, "
              f"within top-10 for {np.mean(np.array(ranks) <= 10):.1%}")
    print(f"  confident mistakes: {cwr}")
    buckets = accuracy_by_separability(per_poly)
    print(f"  {'rho* range':>16} {'n':>5} {'accuracy':>9} {'bound':>8}")
    for b in buckets:
        print(f"  {b['lo']:.3f}-{b['hi']:<10.3f} {b['n']:>5} {b['acc']:>9.1%} "
              f"{1 - b['bound']:>8.1%}")

    results = dict(
        groups=len(pm), types=len(pm.index),
        profile_counts=dict(min=int(pm.counts.min()),
                            median=int(np.median(pm.counts)),
                            max=int(pm.counts.max())),
        corpus=len(rows), in_domain=len(in_dom),
        sample=len(test), margin=args.margin,
        ablation=abl, timing=timing,
        separability=dict(
            rho_median=float(np.median(best)),
            rho_p90=float(np.percentile(best, 90)),
            rho_max=float(best.max()),
            served_at_60=float(np.mean(primes_needed(best, 0.05) <= 60)),
            served_at_60_union=float(np.mean(
                primes_needed(best, 0.05 / (len(pm) - 1)) <= 60)),
            median_primes_needed=float(np.median(
                primes_needed(best, 0.05)[np.isfinite(primes_needed(best, 0.05))])),
            forced_error_mean=float(fe.mean()),
            forced_error_median=float(np.median(fe)),
            forced_above_10=float(np.mean(fe > 0.10)),
            forced_above_25=float(np.mean(fe > 0.25)),
            forced_above_40=float(np.mean(fe > 0.40)),
        ),
        errors=dict(
            n_right=len(right), n_wrong=len(wrong),
            rho_rival_right_median=pct(right, 50),
            rho_rival_wrong_median=pct(wrong, 50),
            rho_rival_right_p90=pct(right, 90),
            rho_rival_wrong_p10=pct(wrong, 10),
            rank_median=int(np.median(ranks)) if ranks else None,
            rank_within_10=float(np.mean(np.array(ranks) <= 10)) if ranks else None,
            confident_mistakes=cwr,
            by_separability=buckets,
        ),
    )
    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
