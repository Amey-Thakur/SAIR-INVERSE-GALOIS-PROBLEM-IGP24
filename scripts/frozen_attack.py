# ==============================================================================
# File: frozen_attack.py
# Description: Attacks the baseline frozen unclaimed pairs. Each such pair has
#   exactly one LMFDB example field, usually far from the minimal
#   discriminant. The attack rebuilds the field family from its own subfield
#   tower: the largest proper subfield S of the baseline polynomial is
#   extracted with nfsubfields, and small conductor relative abelian steps of
#   degree 24/deg(S) are enumerated over S with bnrclassfield, sweeping every
#   archimedean part for signatures. Any candidate whose exact nfdisc is
#   smaller than the baseline discriminant is submitted; the server unlocks
#   the pair if the label matches, and other labels join as ordinary pairs.
# Usage: py scripts/frozen_attack.py [norm_bound]
# Tech Stack: Python 3.10+, PARI/GP 2.15 via wsl, python-flint
# ==============================================================================

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factory as F
from fingerprint import is_irreducible_deg24, real_roots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "batches"

GP_PAIR = r"""
attack(basepol, dbase, rwant, nb, tmax) = {
  my(sf, best, bdeg, S, d, bnf, ids, bnr, subs, abspol, dd, n, i, s,
     r1, aneed, archs, t0, cand = 0, hits = 0);
  sf = iferr(nfsubfields(basepol), e, []);
  best = 0; bdeg = 1;
  for(i = 1, #sf,
    d = poldegree(sf[i][1]);
    if(d > bdeg && d < 24 && (24 % d) == 0, bdeg = d; best = sf[i][1]));
  if(best == 0, print("NOSUB"); return);
  S = polredbest(best);
  d = 24 / bdeg;
  bnf = iferr(bnfinit(S, 1), e, 0);
  if(bnf == 0, print("NOBNF"); return);
  r1 = bnf.sign[1];
  \\ Quadratic steps: each unramified real place of S contributes d real
  \\ embeddings, so the archimedean ramification size is forced by rwant.
  aneed = r1 - rwant / d;
  if(aneed < 0 || aneed > r1, print("NOARCH"); return);
  print("SUBFIELD deg ", bdeg, " step ", d, " r1 ", r1, " aneed ", aneed);
  \\ All arch patterns of the forced size, capped.
  archs = List();
  forvec(v = vector(r1, j, [0, 1]),
    if(vecsum(v) == aneed, listput(archs, v));
    if(#archs >= 24, break));
  ids = ideallist(bnf, nb);
  t0 = getabstime();
  for(n = 1, nb,
    for(i = 1, #ids[n],
      for(a = 1, #archs,
        if(getabstime() - t0 > tmax * 1000, break(3));
        bnr = iferr(bnrinit(bnf, [ids[n][i], archs[a]], 1), e, 0);
        if(bnr == 0, next);
        subs = iferr(subgrouplist(bnr, [d], 1), e, []);
        for(s = 1, #subs,
          abspol = iferr(bnrclassfield(bnr, subs[s], 2), e, 0);
          if(abspol == 0 || poldegree(abspol) != 24, next);
          cand++;
          dd = iferr(abs(nfdisc(abspol)), e, 0);
          if(dd != 0 && dd < dbase && polsturm(abspol) == rwant,
            hits++;
            print("HIT r=", rwant, " disc_digits=", #digits(dd),
                  " : ", Vecrev(Vec(abspol)))));
      );
    );
  );
  print("PAIRDONE cands ", cand, " hits ", hits);
}
"""


def main(nb=20):
    rows = list(csv.DictReader((ROOT / "data" / "lmfdb_baseline.csv")
                               .open(encoding="utf-8")))
    k = {}
    for it in json.loads((ROOT / "data" / "label_progress.json")
                         .read_text(encoding="utf-8")):
        for s in it["signatures"]:
            k[(it["t"], s["r"])] = s["teamCount"]
    base = defaultdict(list)
    for r in rows:
        t = int(r["label"].replace("24T", ""))
        base[(t, int(r["r"]))].append(r)
    frozen = {p: fs[0] for p, fs in base.items()
              if k.get(p, 1) == 0 and len(fs) == 1}
    print(f"attacking {len(frozen)} frozen pairs, norm bound {nb}", flush=True)

    found = []
    for (t, r), f in sorted(frozen.items()):
        dbase = f["nfdisc_abs"]
        script = (GP_PAIR +
                  f"\ndefault(parisizemax, 2048000000);"
                  f"\nattack(Pol(Vecrev([{f['coeffs']}])), {dbase}, {r}, "
                  f"{nb}, 480);\n")
        try:
            out = subprocess.run(["wsl", "-d", "Ubuntu", "--", "gp", "-q"],
                                 input=script, capture_output=True, text=True,
                                 timeout=560).stdout
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or ""
            if isinstance(out, bytes):
                out = out.decode()
        hits = 0
        for line in out.splitlines():
            if line.startswith("HIT "):
                head, _, rest = line.partition(" : ")
                rr = int(head.split("r=")[1].split()[0])
                try:
                    vals = [int(v) for v in
                            rest.strip("[]").replace(" ", "").split(",")]
                except ValueError:
                    continue
                if len(vals) == 25 and vals[24] == 1 and vals[0] != 0 \
                        and is_irreducible_deg24(vals):
                    found.append((vals, f"frozen 24T{t} want_r={r} got_r={rr}"))
                    hits += 1
        status = [l for l in out.splitlines()
                  if l in ("NOSUB", "NOBNF", "NOARCH") or l.startswith(("SUBFIELD","PAIRDONE"))]
        print(f"  24T{t} r={r}: {status} hits {hits}", flush=True)

    print(f"total disc-beating candidates: {len(found)}", flush=True)
    if not found:
        return
    existing = [int(p.stem.split("_")[-1]) for p in OUT.glob("igp24_batch_*.txt")]
    name = f"igp24_batch_{max(existing, default=0) + 1:03d}.txt"
    with (OUT / name).open("w", encoding="ascii", newline="\n") as fh:
        fh.write("# IGP24 frozen pair attack: baseline disc beaters via "
                 "relative class fields.\n")
        for vals, tag in found:
            fh.write(",".join(map(str, vals)) + f" # {tag}\n")
    with (ROOT / "data" / "ledger.jsonl").open("a", encoding="utf-8") as led:
        for vals, tag in found:
            led.write(json.dumps({"coeffs": ",".join(map(str, vals)),
                                  "key": "", "r": real_roots(vals),
                                  "batch": name}) + "\n")
    print(f"wrote batches/{name}: {len(found)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
