# ==============================================================================
# File: pari_sweep.py
# Description: The class field campaign. For every base field K of degree d
#   in {4, 6, 8, 12} it enumerates ray class extensions of degree 24/d over
#   conductors up to a norm bound with every archimedean pattern, taking the
#   absolute degree-24 polynomial from bnrclassfield. Unlike the quadratic
#   twist engines, the abelian layer here can be C3, C4, C6, or any abelian
#   group of the step order, with the Galois action pinned by the chosen ray
#   class subgroup, which is the construction class the unclaimed surface is
#   made of. Output is deduplicated against the ledger, flint checked, and
#   written as submission batches; the server's labels then say which groups
#   were reached.
# Usage: py scripts/pari_sweep.py <base_degree> [minutes] [norm_bound]
# Tech Stack: Python 3.10+, PARI/GP 2.15 via wsl, python-flint
# ==============================================================================

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factory as F
from fingerprint import is_irreducible_deg24, real_roots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "batches"
MAX_ABS = 10 ** 38

GP = r"""
default(parisizemax, 2048000000);
sweep(pol, stepdeg, nb, tmax) = {
  my(bnf, ids, bnr, subs, abspol, r1, t0, produced = 0);
  bnf = iferr(bnfinit(pol, 1), e, 0);
  if(bnf == 0, print("BADBASE"); return);
  r1 = bnf.sign[1];
  ids = ideallist(bnf, nb);
  t0 = getabstime();
  for(n = 1, nb,
    for(i = 1, #ids[n],
      forvec(arch = vector(r1, j, [0, 1]),
        if(getabstime() - t0 > tmax * 1000, print("TIMEUP ", produced); return);
        bnr = iferr(bnrinit(bnf, [ids[n][i], arch], 1), e, 0);
        if(bnr == 0, next);
        \\ cheap pre-check: the ray class group must admit the step order
        if(bnr.no % stepdeg != 0, next);
        subs = iferr(subgrouplist(bnr, [stepdeg], 1), e, []);
        for(s = 1, #subs,
          abspol = iferr(bnrclassfield(bnr, subs[s], 2), e, 0);
          if(abspol == 0 || poldegree(abspol) != 24, next);
          produced++;
          print("P ", Vecrev(Vec(abspol))));
      );
    );
  );
  print("SWEPT ", produced);
}
"""


def collect(stdout, seen, rows):
    got = 0
    for line in stdout.splitlines():
        if not line.startswith("P "):
            continue
        try:
            vals = [int(v) for v in
                    line[2:].strip().strip("[]").replace(" ", "").split(",")]
        except ValueError:
            continue
        if len(vals) != 25 or vals[24] != 1 or vals[0] == 0:
            continue
        if max(abs(v) for v in vals) > MAX_ABS:
            continue
        key = F.canonical(vals)
        if key in seen:
            continue
        seen.add(key)
        if not is_irreducible_deg24(vals):
            continue
        rows.append(vals)
        got += 1
    return got


def flush_rows(rows, tag):
    if not rows:
        return 0
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    idx = max(existing, default=0) + 1
    ledger = (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8")
    written = 0
    for start in range(0, len(rows), 1000):
        chunk = rows[start:start + 1000]
        name = f"igp24_batch_{idx:03d}.txt"
        with (OUT / name).open("w", encoding="ascii", newline="\n") as fh:
            fh.write(f"# IGP24 class field sweep: {tag}.\n")
            for vals in chunk:
                fh.write(",".join(map(str, vals)) +
                         f" # cft {tag} r={real_roots(vals)}\n")
        for vals in chunk:
            ledger.write(json.dumps({
                "coeffs": ",".join(map(str, vals)), "key": "",
                "r": real_roots(vals), "batch": name}) + "\n")
        print(f"wrote batches/{name}: {len(chunk)}", flush=True)
        idx += 1
        written += len(chunk)
    ledger.close()
    return written


def main(base_degree, minutes=120.0, nb=120):
    step = 24 // base_degree
    groups = []
    for raw in (ROOT / "data" / "nf_small.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            g = json.loads(raw)
            if g.get("degree") == base_degree and g.get("fields"):
                groups.append(g)
    if base_degree == 12:
        groups = []
        for raw in (ROOT / "data" / "nf12.jsonl").read_text(encoding="utf-8").splitlines():
            if raw.strip():
                g = json.loads(raw)
                if g.get("fields"):
                    g["degree"] = 12
                    groups.append(g)
    print(f"base degree {base_degree} step {step}: {len(groups)} groups",
          flush=True)

    seen = set()
    for raw in (ROOT / "data" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            try:
                seen.add(F.canonical(
                    [int(v) for v in json.loads(raw)["coeffs"].split(",")]))
            except Exception:
                pass
    print(f"ledger: {len(seen)}", flush=True)

    deadline = time.monotonic() + minutes * 60
    rows = []
    bases = []
    for g in groups:
        for fld in g["fields"][:12]:
            bases.append((g["label"], fld["coeffs"]))
    print(f"bases: {len(bases)}", flush=True)

    for label, coeffs in bases:
        if time.monotonic() > deadline:
            break
        per_base = min(300.0, max(60.0, (deadline - time.monotonic())
                                  / max(1, len(bases)) * 3))
        poly = "+".join(f"({c})*y^{i}" for i, c in enumerate(coeffs) if c)
        script = GP + f"\nsweep({poly}, {step}, {nb}, {int(per_base)});\n"
        try:
            out = subprocess.run(["wsl", "-d", "Ubuntu", "--", "gp", "-q"],
                                 input=script, capture_output=True, text=True,
                                 timeout=per_base + 120).stdout
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or ""
            if isinstance(out, bytes):
                out = out.decode(errors="replace")
        got = collect(out, seen, rows)
        if got:
            print(f"  {label}: +{got} (total {len(rows)})", flush=True)
        if len(rows) >= 4000:
            flush_rows(rows, f"deg{base_degree}")
            rows = []
    flush_rows(rows, f"deg{base_degree}")
    print("sweep complete", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]),
         float(sys.argv[2]) if len(sys.argv) > 2 else 120.0,
         int(sys.argv[3]) if len(sys.argv) > 3 else 120)
