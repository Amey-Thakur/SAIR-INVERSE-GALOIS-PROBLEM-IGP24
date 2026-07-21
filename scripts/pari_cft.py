# ==============================================================================
# File: pari_cft.py
# Description: Class field theory factory through PARI/GP in WSL. Builds
#   degree-24 absolute fields as ray class fields: for each base field K it
#   enumerates moduli up to a norm bound with every archimedean part, lists
#   ray class subgroups of the complementary index with conductor equal to
#   the modulus, and calls bnrclassfield(bnr, H, 2) for the absolute
#   polynomial. This is the construction the unclaimed score surface is made
#   of, and the archimedean components sweep the real root signature. Output
#   is post-filtered in Python: monic degree 24 integer, coefficient bound,
#   irreducibility, canonical dedupe against the ledger.
# Usage: py scripts/pari_cft.py quad2 | quad12 | cubic8 [norm_bound]
#   quad12: real and imaginary quadratic bases, degree 12 ray class steps
#   cubic8: cubic bases, degree 8 ray class steps
#   quartic6 / sextic4 / oct3: higher degree bases, smaller steps
# Tech Stack: Python 3.10+, PARI/GP 2.15 via wsl subprocess, python-flint
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
MAX_ABS = 10 ** 40

GP_TEMPLATE = r"""
default(parisizemax, 2048000000);
step(pol, deg, nb) = {
  my(bnf, ids, bnr, subs, ab);
  bnf = iferr(bnfinit(pol, 1), e, 0);
  if(bnf == 0, return);
  my(r1 = bnf.sign[1]);
  ids = ideallist(bnf, nb);
  for(n = 2, nb,
    for(i = 1, #ids[n],
      forvec(arch = vector(r1, j, [0,1]),
        my(mod = [ids[n][i], arch]);
        bnr = iferr(bnrinit(bnf, mod, 1), e, 0);
        if(bnr == 0, next);
        subs = iferr(subgrouplist(bnr, [deg], 1), e, []);
        for(s = 1, #subs,
          my(abs = iferr(bnrclassfield(bnr, subs[s], 2), e, 0));
          if(abs == 0, next);
          if(poldegree(abs) == 24,
            print("POLY:", Vecrev(Vec(abs)))));
      );
    );
  );
}
"""


def gp_run(script, timeout):
    try:
        proc = subprocess.run(
            ["wsl", "-d", "Ubuntu", "--", "gp", "-q", "-f"],
            input=script, capture_output=True, text=True, timeout=timeout,
        )
        return proc.stdout
    except subprocess.TimeoutExpired as exc:
        return (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) \
            else (exc.stdout or "")


def collect(stdout, seen, rows, tag):
    got = 0
    for line in stdout.splitlines():
        if not line.startswith("POLY:"):
            continue
        try:
            vals = [int(v) for v in
                    line[5:].strip().strip("[]").replace(" ", "").split(",")]
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
        rows.append((vals, f"cft {tag} r={real_roots(vals)}"))
        got += 1
    return got


def flush_rows(rows):
    if not rows:
        return
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    idx = max(existing, default=0) + 1
    ledger = (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8")
    for start in range(0, len(rows), 1000):
        chunk = rows[start:start + 1000]
        name = f"igp24_batch_{idx:03d}.txt"
        with (OUT / name).open("w", encoding="ascii", newline="\n") as fh:
            fh.write("# IGP24 class field wave: ray class fields via PARI.\n")
            for vals, tag in chunk:
                fh.write(",".join(map(str, vals)) + f" # {tag}\n")
        for vals, tag in chunk:
            ledger.write(json.dumps({
                "coeffs": ",".join(map(str, vals)),
                "key": "", "r": real_roots(vals), "batch": name,
            }) + "\n")
        print(f"wrote batches/{name}: {len(chunk)} lines", flush=True)
        idx += 1
    ledger.close()


def bases_for(mode):
    if mode == "quad12":
        ds = [d for d in list(range(2, 60)) + list(range(-1, -40, -1))
              if squarefree(d) and d != 1]
        return [(f"y^2-({d})", 12, 40, f"quad d={d}") for d in ds]
    if mode == "cubic8":
        polys = []
        for a in range(-6, 7):
            for b in range(1, 12):
                pol = f"y^3+({a})*y+({b})"
                polys.append((pol, 8, 25, f"cubic a={a} b={b}"))
        return polys
    if mode == "quartic6":
        return [(f"y^4-({c})*y^2+({d})", 6, 20, f"quartic c={c} d={d}")
                for c in range(-5, 8) for d in range(-6, 7) if d != 0]
    raise SystemExit(f"unknown mode {mode}")


def squarefree(n):
    n = abs(n)
    if n < 2:
        return n == 1
    for p in range(2, int(n ** 0.5) + 1):
        if n % (p * p) == 0:
            return False
    return True


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "quad12"
    seen = set()
    for raw in (ROOT / "data" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rec = json.loads(raw)
            try:
                seen.add(F.canonical([int(v) for v in rec["coeffs"].split(",")]))
            except Exception:
                pass
    print(f"ledger seen: {len(seen)}", flush=True)

    rows = []
    started = time.time()
    for pol, deg, nb, tag in bases_for(mode):
        script = GP_TEMPLATE + f'\nstep({pol}, {deg}, {nb});\n'
        got = collect(gp_run(script, 900), seen, rows, tag)
        print(f"  {tag}: +{got} (total {len(rows)}, "
              f"{int(time.time()-started)}s)", flush=True)
        if len(rows) >= 6000:
            break
    flush_rows(rows)
    print(f"done: {len(rows)} fields in {int(time.time()-started)}s")


if __name__ == "__main__":
    main()
