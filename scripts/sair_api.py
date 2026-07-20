# ==============================================================================
# File: sair_api.py
# Description: The feedback loop with the competition server. Three commands:
#   `remaining` saves the (24Tt, r) pairs no participant team has claimed
#   yet (each is worth a full point to its first finder), `submit` posts one
#   or more batch files, and `results` lists recent submissions with their
#   acceptance counts. Requires an API key with competition.read (and
#   competition.write for submit) in the SAIR_API_KEY environment variable.
# Usage: py scripts/sair_api.py remaining
#        py scripts/sair_api.py submit batches/igp24_batch_001.txt [...]
#        py scripts/sair_api.py results
# Tech Stack: Python 3.10+, Requests
# ==============================================================================

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = "https://api.sair.foundation/api/public/v1/competitions/igp24"
ROOT = Path(__file__).resolve().parents[1]


def _headers():
    key = os.environ.get("SAIR_API_KEY", "")
    if not key:
        sys.exit("SAIR_API_KEY is not set. Create one at "
                 "https://id.sair.foundation/profile/api-keys and export it.")
    return {"Authorization": f"Bearer {key}"}


def _unwrap(payload):
    """Peel the {"ok": true, "data": ...} envelope the API returns."""
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def _items(data):
    """Find the list of records inside a possibly nested response body."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "submissions", "pairs", "results"):
            if key in data:
                return _items(data[key])
    return []


def _clean_line(raw):
    """A submittable line: the 25 coefficients, keeping only a
    poly_disc_primes hint from any trailing comment."""
    coeffs = raw.split("#", 1)[0].strip()
    if "poly_disc_primes=" in raw:
        hint = "poly_disc_primes=" + raw.split("poly_disc_primes=", 1)[1].split()[0]
        return f"{coeffs} # {hint}"
    return coeffs


def remaining():
    """Page through every unclaimed (24Tt, r) pair and save the list."""
    pairs, cursor = [], None
    while True:
        params = {"limit": 5000}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(f"{BASE}/remaining-pairs", headers=_headers(),
                            params=params, timeout=60)
        resp.raise_for_status()
        body = _unwrap(resp.json())
        page = _items(body)
        pairs.extend(page)
        cursor = (body.get("nextCursor") or body.get("cursor")) if isinstance(body, dict) else None
        if not cursor or not page:
            break

    out = ROOT / "data" / "remaining_pairs.json"
    out.write_text(json.dumps(pairs, indent=1), encoding="utf-8")
    print(f"unclaimed pairs: {len(pairs)}, saved to {out.relative_to(ROOT)}")


def submit(paths):
    """Post each batch file as one submission. One POST is one submission
    against the daily cap, no matter how many polynomials it carries."""
    for path in paths:
        lines = [
            _clean_line(s.strip())
            for s in Path(path).read_text(encoding="utf-8").splitlines()
            if s.strip() and not s.strip().startswith("#")
        ]
        resp = requests.post(
            f"{BASE}/submissions", headers=_headers(),
            json={"payload": {"polynomials": lines}}, timeout=180,
        )
        if resp.ok:
            body = _unwrap(resp.json())
            sub_id = body.get("submissionId", "") if isinstance(body, dict) else ""
            print(f"{path}: {len(lines)} polynomials submitted, id {sub_id}")
        else:
            print(f"{path}: HTTP {resp.status_code}")
            print(" ", resp.text[:400])
            break
        time.sleep(2)   # be polite to the evaluator queue


def results():
    resp = requests.get(f"{BASE}/submissions/me", headers=_headers(),
                        params={"limit": 20}, timeout=60)
    resp.raise_for_status()
    items = _items(_unwrap(resp.json()))
    if not items:
        print("no submissions found")
        return
    for item in items:
        ok = len(item.get("verifiedPolynomials", []) or [])
        bad = len(item.get("failedPolynomials", []) or [])
        queued = len((item.get("payload", {}) or {}).get("queuedPolynomials", []) or [])
        print(f"{item.get('submissionId', '')}  created {item.get('createdAt', '')}")
        print(f"  verified {ok}, failed {bad}, queued {queued}")


def labels():
    """Join the server's per-polynomial verification results (label, r,
    scoreability, discriminant) back onto our submitted coefficient lines.
    polynomialIndex follows submitted line order, so the local batch file
    gives the coefficients the server does not echo. Output feeds the
    factory's label-aware exclusions."""
    mapping = json.loads((ROOT / "data" / "submissions_map.json").read_text())
    out = ROOT / "data" / "labels.jsonl"
    total = 0
    with out.open("w", encoding="utf-8") as fh:
        for sub_id, fname in mapping.items():
            lines = [
                s.split("#", 1)[0].strip()
                for s in (ROOT / fname).read_text(encoding="utf-8").splitlines()
                if s.strip() and not s.strip().startswith("#")
            ]
            resp = requests.get(f"{BASE}/submissions/{sub_id}",
                                headers=_headers(), timeout=120)
            resp.raise_for_status()
            rows = _unwrap(resp.json()).get("verifiedPolynomials") or []
            for row in rows:
                idx = row.get("polynomialIndex")
                if idx is None or idx >= len(lines):
                    continue
                fh.write(json.dumps({
                    "coeffs": lines[idx],
                    "label": row.get("label"),
                    "t": row.get("t"),
                    "r": row.get("r"),
                    "scoreable": row.get("scoreable"),
                    "inBaseline": row.get("inBaseline"),
                    "fieldDiscAbs": row.get("fieldDiscAbs"),
                }) + "\n")
                total += 1
    print(f"labels for {total} polynomials saved to {out.relative_to(ROOT)}")


def main():
    commands = {"remaining": remaining, "results": results, "labels": labels}
    if len(sys.argv) < 2 or sys.argv[1] not in (*commands, "submit"):
        sys.exit(__doc__ or "usage: sair_api.py remaining|submit|results|labels")
    if sys.argv[1] == "submit":
        if len(sys.argv) < 3:
            sys.exit("submit needs at least one batch file")
        submit(sys.argv[2:])
    else:
        commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
