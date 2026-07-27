# ==============================================================================
# File: cyclotomic.py
# Description: Constructs abelian degree-24 fields as subfields of cyclotomic
#   fields, the pairs no search engine reaches. A degree-24 field with an
#   order-24 Galois group is Galois, so bulk random search (which produces
#   non-Galois fields of measure one) never lands on it, which is why the
#   three abelian groups of order 24 sit undiscovered on the board. PARI's
#   polsubcyclo returns every degree-24 subfield of Q(zeta_n); polsturm gives
#   the exact real root count, so both the totally real (r=24) and CM (r=0)
#   realizations are produced directly. Output is deduplicated by reduced
#   defining polynomial and written as a submission batch.
# Usage: py scripts/cyclotomic.py [nmax]
# Tech Stack: Python 3.10+, PARI/GP 2.15 via wsl, python-flint
# ==============================================================================

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factory as F
from fingerprint import is_irreducible_deg24, real_roots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "batches"

GP = r"""
gen(nmax) = {
  my(n, pols, p, i);
  for(n = 5, nmax,
    if(eulerphi(n) % 24 != 0, next);
    pols = iferr(polsubcyclo(n, 24), e, 0);
    if(pols == 0, next);
    if(type(pols) == "t_POL", pols = [pols]);
    for(i = 1, #pols,
      p = pols[i];
      if(poldegree(p) == 24 && polisirreducible(p),
        print("F ", n, " ", polsturm(p), " ", Vecrev(Vec(p)))));
  );
}
gen(NMAX);
print("DONE");
"""


def reduce_polys(coeff_rows):
    """polredbest each polynomial to its smallest discriminant model."""
    script = ["default(parisizemax, 1024000000);"]
    for row in coeff_rows:
        body = ",".join(map(str, row))
        script.append(
            f"iferr(print(Vecrev(Vec(polredbest(Pol(Vecrev([{body}])))))),"
            f"e,print(\"F\"));")
    out = subprocess.run(["wsl", "-d", "Ubuntu", "--", "gp", "-q"],
                         input="\n".join(script), capture_output=True,
                         text=True, timeout=1200).stdout
    reduced = []
    rows = [l.strip() for l in out.splitlines() if l.strip().startswith("[")]
    for original, line in zip(coeff_rows, rows):
        try:
            vals = [int(v) for v in line.strip("[]").replace(" ", "").split(",")]
            reduced.append(vals if len(vals) == 25 and vals[24] == 1 else original)
        except ValueError:
            reduced.append(original)
    if len(rows) != len(coeff_rows):
        return coeff_rows
    return reduced


def main(nmax=4000):
    out = subprocess.run(["wsl", "-d", "Ubuntu", "--", "gp", "-q"],
                         input=GP.replace("NMAX", str(nmax)),
                         capture_output=True, text=True, timeout=3000).stdout
    rows = []
    for line in out.splitlines():
        if not line.startswith("F "):
            continue
        _, n, r, rest = line.split(" ", 3)
        coeffs = [int(v) for v in rest.strip("[]").replace(" ", "").split(",")]
        if len(coeffs) == 25 and coeffs[24] == 1 and coeffs[0] != 0:
            rows.append((coeffs, int(r), int(n)))
    print(f"raw abelian fields: {len(rows)}", flush=True)

    seen, uniq = set(), []
    for coeffs, r, n in rows:
        key = F.canonical(coeffs)
        if key in seen or not is_irreducible_deg24(coeffs):
            continue
        seen.add(key)
        uniq.append((coeffs, r, n))
    print(f"distinct irreducible: {len(uniq)}", flush=True)

    reduced = reduce_polys([c for c, _, _ in uniq])
    final, seen2 = [], set()
    for (coeffs, r, n), red in zip(uniq, reduced):
        key = F.canonical(red)
        if key in seen2:
            continue
        seen2.add(key)
        final.append((red, real_roots(red), n))

    from collections import Counter
    print("signature spread:", dict(Counter(r for _, r, _ in final)))
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    name = f"igp24_batch_{max(existing, default=0) + 1:03d}.txt"
    with (OUT / name).open("w", encoding="ascii", newline="\n") as fh:
        fh.write("# IGP24 cyclotomic wave: abelian degree-24 fields "
                 "(subfields of Q(zeta_n)).\n")
        for coeffs, r, n in final:
            fh.write(",".join(map(str, coeffs)) + f" # cyclo n={n} r={r}\n")
    with (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8") as ledger:
        for coeffs, r, n in final:
            ledger.write(json.dumps({
                "coeffs": ",".join(map(str, coeffs)), "key": "",
                "r": r, "batch": name}) + "\n")
    print(f"wrote batches/{name}: {len(final)} abelian fields")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4000)
