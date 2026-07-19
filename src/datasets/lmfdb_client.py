# ==============================================================================
# File: lmfdb_client.py
# Description: Loads the frozen LMFDB-derived IGP24 baseline and answers the two
#   questions a search planner needs: which (24Tt, r) pairs are already known,
#   and what exact nfdisc a submission must beat to unlock a baseline pair. It
#   reads the committed data/lmfdb_baseline.csv, and fetches that file from the
#   competition download if it is missing. Every number comes straight from the
#   official baseline file, nothing hardcoded.
# Tech Stack: Python 3.10+, Requests
# ==============================================================================

from __future__ import annotations

import csv
from pathlib import Path

BASELINE_URL = "https://competition.sair.foundation/downloads/igp24/lmfdb_baseline.csv"
BASELINE_PATH = Path(__file__).resolve().parents[2] / "data" / "lmfdb_baseline.csv"


def _rows() -> list[dict]:
    if not BASELINE_PATH.exists():
        import requests

        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        text = requests.get(BASELINE_URL, timeout=60).text
        BASELINE_PATH.write_text(text, encoding="utf-8")

    with BASELINE_PATH.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_baseline() -> dict[tuple[str, int], int]:
    """Map each baseline (label, r) pair to D_base, the smallest exact nfdisc
    recorded for that pair. A participant unlocks the pair only with an exact
    nfdisc strictly below this value."""
    thresholds: dict[tuple[str, int], int] = {}

    for row in _rows():
        pair = (row["label"], int(row["r"]))
        disc = int(row["nfdisc_abs"])
        if pair not in thresholds or disc < thresholds[pair]:
            thresholds[pair] = disc

    return thresholds


def summary() -> dict[str, int]:
    baseline = load_baseline()
    labels = {label for label, _ in baseline}
    return {"labels": len(labels), "pairs": len(baseline)}


if __name__ == "__main__":
    s = summary()
    print(f"Baseline: {s['labels']} distinct 24Tt labels, {s['pairs']} distinct (24Tt, r) pairs.")
    print("A non-baseline pair scores outright; a baseline pair scores only with")
    print("an exact nfdisc strictly below the recorded threshold for that pair.")
