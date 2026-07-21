# ==============================================================================
# File: polred.py
# Description: Reduces batch polynomials with PARI's polredbest, run through
#   GP inside WSL Ubuntu. polredbest returns a defining polynomial of the
#   same number field with the smallest known discriminant representative,
#   which raises the score ratio log(D0)/log(D) and keeps the server's
#   60 second nfdisc within budget. Lines whose reduction times out or fails
#   are kept unchanged, so the output batch always has the same field on
#   every line as the input batch.
# Usage: py scripts/polred.py batches/igp24_batch_NNN.txt [...]
# Tech Stack: Python 3.10+, PARI/GP 2.15 via wsl subprocess
# ==============================================================================

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def reduce_batch(path):
    lines = path.read_text(encoding="ascii").splitlines()
    polys = []
    for line in lines:
        body = line.split("#")[0].strip()
        if body:
            polys.append(body)
    script = ["default(parisizemax, 1024000000);"]
    for body in polys:
        script.append(
            f"iferr(print(Vecrev(Vec(polredbest(Pol(Vecrev([{body}])))))),"
            f"e,print(\"FAIL\"));")
    proc = subprocess.run(
        ["wsl", "-d", "Ubuntu", "--", "gp", "-q", "-f"],
        input="\n".join(script), capture_output=True, text=True, timeout=5400,
    )
    out = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    if len(out) != len(polys):
        print(f"{path.name}: gp returned {len(out)} rows for {len(polys)} "
              f"polys, batch left unchanged")
        return 0
    reduced = 0
    new_lines = []
    idx = 0
    for line in lines:
        body, _, tag = line.partition("#")
        if not body.strip():
            new_lines.append(line)
            continue
        row = out[idx]
        idx += 1
        if row != "FAIL" and row.startswith("["):
            vals = row.strip("[]").replace(" ", "").split(",")
            if len(vals) == 25 and vals != body.strip().split(","):
                old = max(abs(int(v)) for v in body.strip().split(","))
                new = max(abs(int(v)) for v in vals)
                if new < old:
                    line = ",".join(vals) + (f" #{tag}" if tag else "")
                    reduced += 1
        new_lines.append(line)
    path.write_text("\n".join(new_lines) + "\n", encoding="ascii", newline="\n")
    print(f"{path.name}: reduced {reduced} of {len(polys)}")
    return reduced


def main():
    for arg in sys.argv[1:]:
        reduce_batch(ROOT / arg if not Path(arg).is_absolute() else Path(arg))


if __name__ == "__main__":
    main()
