# ==============================================================================
# File: targeted2.py
# Description: Closed loop signature targeter. The graded ledger shows 188
#   labels we already produce that still have unclaimed signatures, worth up
#   to one point each. The producing families (totally real towers, tower
#   chains, composita) emit the same label across several signatures, so this
#   run replays those engines, keeps only candidates whose real root count is
#   a needed signature, and confirms the label locally by matching the
#   Frobenius fingerprint against fingerprints already graded to that label.
#   A fingerprint that maps to exactly one label identifies it with the
#   validated 98.5 percent precision, so every kept line is a near certain
#   claim of an unclaimed pair.
# Usage: py scripts/targeted2.py [minutes]
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
from fingerprint import group_key, is_irreducible_deg24, real_roots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "batches"


def load_targets():
    k = defaultdict(lambda: -1)
    for it in json.loads((ROOT / "data" / "label_progress.json").read_text(encoding="utf-8")):
        for s in it.get("signatures", []):
            k[(it["t"], s["r"])] = s.get("teamCount", 0)
    lab = {}
    for raw in (ROOT / "data" / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(raw)
        lab[rec["coeffs"]] = (rec["t"], rec["r"])
    ours = defaultdict(set)
    for t, r in lab.values():
        ours[t].add(r)
    needed = defaultdict(set)          # t -> unclaimed signatures
    for t, rs in ours.items():
        for r in range(0, 26, 2):
            if r not in rs and k[(t, r)] == 0:
                needed[t].add(r)
    # fingerprint -> label, unambiguous keys only
    key2t = defaultdict(set)
    for raw in (ROOT / "data" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rec = json.loads(raw)
            if rec["coeffs"] in lab:
                key2t[rec["key"]].add(lab[rec["coeffs"]][0])
    key2label = {kh: next(iter(ts)) for kh, ts in key2t.items()
                 if len(ts) == 1 and next(iter(ts)) in needed}
    return needed, key2label


def main(minutes=25.0):
    needed, key2label = load_targets()
    total = sum(len(v) for v in needed.values())
    want_r = set().union(*needed.values()) if needed else set()
    print(f"targets: {len(needed)} labels, {total} unclaimed signatures, "
          f"{len(key2label)} usable fingerprints", flush=True)

    hits, claimed = [], set()
    started = time.time()
    stats = defaultdict(int)
    engines = [(F.engine_totally_real, 500), (F.engine_towers, 1500),
               (F.engine_compose, 300), (F.engine_composita, 300)]
    while time.time() - started < minutes * 60:
        for engine, count in engines:
            for coeffs, tag in engine(count):
                if coeffs is None or len(coeffs) != 25:
                    continue
                stats["raw"] += 1
                r = real_roots(coeffs)
                if r not in want_r:
                    continue
                if not is_irreducible_deg24(coeffs):
                    continue
                stats["irr"] += 1
                kh = F.key_hash(group_key(coeffs))
                t = key2label.get(kh)
                if t is None or r not in needed[t] or (t, r) in claimed:
                    continue
                claimed.add((t, r))
                hits.append((coeffs, f"target 24T{t} r={r}", kh, r))
                print(f"  HIT 24T{t} r={r} via {tag.split()[0] if tag else '?'}"
                      f" ({len(hits)} total)", flush=True)
            if time.time() - started >= minutes * 60:
                break
        print(f"  {int(time.time()-started)}s raw {stats['raw']} irr "
              f"{stats['irr']} hits {len(hits)}", flush=True)

    if not hits:
        print("no hits this run")
        return
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    name = f"igp24_batch_{max(existing, default=0) + 1:03d}.txt"
    with (OUT / name).open("w", encoding="ascii", newline="\n") as fh:
        fh.write("# IGP24 targeted wave: held labels at unclaimed signatures.\n")
        for coeffs, tag, kh, r in hits:
            fh.write(",".join(map(str, coeffs)) + f" # {tag}\n")
    with (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8") as ledger:
        for coeffs, tag, kh, r in hits:
            ledger.write(json.dumps({
                "coeffs": ",".join(map(str, coeffs)),
                "key": kh, "r": r, "batch": name,
            }) + "\n")
    print(f"wrote batches/{name}: {len(hits)} targeted claims")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 25.0)
