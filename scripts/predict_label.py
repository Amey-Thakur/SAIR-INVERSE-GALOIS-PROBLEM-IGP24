# ==============================================================================
# File: predict_label.py
# Description: Names a polynomial's Galois group without Magma. The Frobenius
#   cycle types observed at many primes are, by Chebotarev, samples from the
#   group's own cycle-type distribution; scoring the observations against the
#   profile of every candidate group (group_profiles.jsonl) ranks the
#   possible 24Tt labels. Run as a script it validates the predictor against
#   every polynomial the competition server has already labeled for us, which
#   is the ground truth that decides how far the targeting can be trusted.
# Usage: py scripts/predict_label.py [--sample N]
# Tech Stack: Python 3.10+, python-flint
# ==============================================================================

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import cycle_pattern

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "data" / "group_profiles.jsonl"

# More primes than the clustering fingerprint uses: prediction needs the
# extra resolution, and at half a millisecond per prime it stays cheap.
PRED_PRIMES = [101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157,
               163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227,
               229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283,
               293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367,
               373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439]


class Predictor:
    def __init__(self, profiles_path=PROFILES):
        self.groups = []
        for raw in profiles_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            rec = json.loads(raw)
            total = sum(rec["types"].values())
            dist = {
                tuple(int(x) for x in key.split(",")): count / total
                for key, count in rec["types"].items()
            }
            self.groups.append((rec["t"], dist))

    def observe(self, coeffs):
        """Cycle types of the polynomial at the prediction primes."""
        seen = []
        for p in PRED_PRIMES:
            pat = cycle_pattern(coeffs, p)
            if pat is not None:
                seen.append(pat)
        return seen

    def predict(self, coeffs, top=3):
        """Ranked (t, log-likelihood) candidates for the polynomial's label.
        A group whose profile lacks an observed type is not eliminated
        outright, only heavily penalized: the profiles are sampled, so a
        rare type can be absent from a finite sample."""
        obs = self.observe(coeffs)
        if not obs:
            return []
        floor = math.log(1e-4)
        scored = []
        for t, dist in self.groups:
            score = 0.0
            for pat in obs:
                p = dist.get(pat)
                score += math.log(p) if p else floor
            scored.append((score, t))
        scored.sort(reverse=True)
        return [(t, s) for s, t in scored[:top]]

    def confident(self, coeffs, margin=8.0):
        """The single predicted label when the best candidate beats the
        runner-up by a clear likelihood margin, else None."""
        ranked = self.predict(coeffs, top=2)
        if not ranked:
            return None
        if len(ranked) == 1 or ranked[0][1] - ranked[1][1] >= margin:
            return ranked[0][0]
        return None


def validate(sample_n):
    """Score the predictor against every server-labeled polynomial."""
    import random

    rng = random.Random(2024)
    rows = [json.loads(l)
            for l in (ROOT / "data" / "labels.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    rng.shuffle(rows)
    rows = rows[:sample_n]

    predictor = Predictor()
    print(f"profiles: {len(predictor.groups)} groups | validating on {len(rows)} labeled polynomials")

    top1 = conf_right = conf_wrong = abstain = 0
    for i, rec in enumerate(rows):
        coeffs = [int(v) for v in rec["coeffs"].split(",")]
        truth = rec["t"]
        ranked = predictor.predict(coeffs, top=1)
        if ranked and ranked[0][0] == truth:
            top1 += 1
        sure = predictor.confident(coeffs)
        if sure is None:
            abstain += 1
        elif sure == truth:
            conf_right += 1
        else:
            conf_wrong += 1
        if (i + 1) % 200 == 0:
            print(f"  {i + 1} done", flush=True)

    n = len(rows)
    print(f"top-1 accuracy: {top1}/{n} = {top1 / n:.1%}")
    decided = conf_right + conf_wrong
    print(f"confident predictions: {decided}/{n} "
          f"({conf_right} right, {conf_wrong} wrong"
          f"{', precision ' + format(conf_right / decided, '.1%') if decided else ''})")
    print(f"abstained: {abstain}/{n}")


if __name__ == "__main__":
    n = 1000
    if "--sample" in sys.argv:
        n = int(sys.argv[sys.argv.index("--sample") + 1])
    validate(n)
