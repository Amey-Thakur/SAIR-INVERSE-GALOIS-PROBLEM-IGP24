#!/usr/bin/env python3
"""Build the animated card for a SAIR competition repository.

Original artwork in the palette these repositories already use, so the animation
can live in the repository and be attached to a post without borrowing the
competition site's own canvas.

Every number on these cards is real. The polynomial is an actual submitted
degree-24 totally real polynomial from batches/igp24_batch_001.txt. The modular
arithmetic example is asserted at build time, so the card cannot ship an answer
that is not the answer. Results come from the final leaderboards.

    python .github/scripts/build_animation.py .github/assets

Pillow only.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (0x34, 0x08, 0x25)
PANEL = (0x3E, 0x0E, 0x2C)
EDGE = (0x6B, 0x2F, 0x4F)
INK = (0xF5, 0xF5, 0xF5)
DIM = (0xA5, 0x9C, 0xA1)
ROSE = (0xC9, 0xA9, 0xB8)
PALE = (0xD8, 0xD2, 0xD6)
FRAMES, MS = 30, 90
M = 56

MONO = "C:/Windows/Fonts/consola.ttf"
SEMI = "C:/Windows/Fonts/seguisb.ttf"
UI = "C:/Windows/Fonts/segoeui.ttf"
MARK = Path(__file__).resolve().parent.parent / "assets" / "sair-mark.png"

_fc = {}


def f(path, size):
    if (path, size) not in _fc:
        _fc[(path, size)] = ImageFont.truetype(path, size)
    return _fc[(path, size)]


POLY = [226799, 0, -1428480, 0, 3891072, 0, -6023552, 0, 5864088, 0, -3759360,
        0, 1620320, 0, -472800, 0, 93111, 0, -12160, 0, 1008, 0, -48, 0, 1]
assert len(POLY) == 25 and POLY[24] == 1

MA = 899103931720020664803112403539014024235081614551514303856286
MB = 221181697460058495186708365032735781343414741683850746968064
MP = 596327988844210909256107317539864661837075935433491138146031
MR = 88693848663360565967763879529898350263660463739980652355705
assert (MA * MB) % MP == MR, "the card must not ship a wrong remainder"


def sup(n):
    return str(n).translate(str.maketrans(
        "0123456789", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079"))


def poly_terms():
    out = []
    for k in range(24, -1, -1):
        c = POLY[k]
        if c == 0:
            continue
        sign = "\u2212 " if c < 0 else ("" if not out else "+ ")
        mag = "" if abs(c) == 1 and k else str(abs(c))
        var = "x" + sup(k) if k > 1 else ("x" if k == 1 else "")
        out.append(f"{sign}{mag}{var}")
    return out


def panel(d, box, active=False):
    d.rounded_rectangle(box, radius=12, fill=PANEL,
                        outline=ROSE if active else EDGE, width=2 if active else 1)


def head(im, d, title, sub):
    mark = Image.open(MARK).convert("RGBA").resize((54, 54), Image.LANCZOS)
    im.paste(mark, (M, 28), mark)
    d.text((M + 68, 34), "SAIR", font=f(SEMI, 25), fill=INK)
    d.text((M + 68, 63), "Foundation for Science and AI Research", font=f(UI, 13), fill=DIM)
    d.text((M, 104), title, font=f(SEMI, 38), fill=INK)
    d.text((M + 2, 152), sub, font=f(UI, 18), fill=ROSE)
    d.line([M, 186, W - M, 186], fill=EDGE)


def stats(d, y, cells):
    d.line([M, y, W - M, y], fill=EDGE)
    span = (W - 2 * M) / len(cells)
    for i, (big, small) in enumerate(cells):
        x = M + span * i
        d.text((x, y + 16), big, font=f(SEMI, 26), fill=INK)
        d.text((x + 2, y + 50), small, font=f(UI, 13), fill=DIM)


def foot(d, right):
    d.line([M, H - 62, W - M, H - 62], fill=EDGE)
    d.text((M, H - 48), "Amey Thakur", font=f(SEMI, 17), fill=INK)
    d.text((M, H - 26), "github.com/Amey-Thakur", font=f(MONO, 13), fill=ROSE)
    w = d.textlength(right, font=f(MONO, 13))
    d.text((W - M - w, H - 26), right, font=f(MONO, 13), fill=DIM)


def pipeline(d, t, boxes):
    x, wbox = M, 336
    for k, (a, b) in enumerate(boxes):
        on = k <= (t * 3) % 3 < k + 1
        panel(d, [x, 214, x + wbox, 320], active=on)
        d.text((x + 20, 240), a, font=f(MONO, 17), fill=INK if on else PALE)
        d.text((x + 20, 274), b, font=f(UI, 13), fill=ROSE if on else DIM)
        if k < 2:
            prog = max(0.0, min(1.0, ((t * 3) % 3 - k) * 2))
            d.line([x + wbox + 6, 267, x + wbox + 46, 267], fill=EDGE, width=2)
            d.line([x + wbox + 6, 267, x + wbox + 6 + int(40 * prog), 267], fill=ROSE, width=3)
        x += wbox + 52


def igp24(i):
    t = i / FRAMES
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    head(im, d, "Inverse Galois Problem",
         "Degree 24 over Q. Which finite groups occur as Galois groups?")

    panel(d, [M, 206, 726, 386])
    d.text((M + 22, 220), "A polynomial this factory submitted, totally real, r = 24",
           font=f(UI, 13), fill=DIM)
    terms = poly_terms()
    shown = 1 + int((len(terms) - 1) * min(1.0, t * 1.3))
    line, lines = "", []
    for term in terms[:shown]:
        trial = (line + " " + term).strip()
        if d.textlength(trial, font=f(MONO, 16)) > 610:
            lines.append(line)
            line = term
        else:
            line = trial
    lines.append(line)
    d.text((M + 22, 250), "f(x) =", font=f(MONO, 16), fill=ROSE)
    for k, ln in enumerate(lines[:5]):
        d.text((M + 22, 276 + k * 24), ln, font=f(MONO, 16), fill=PALE)

    ox, oy, R = 960, 300, 78
    pts = [(ox + R * math.cos(a - math.pi / 2), oy + R * math.sin(a - math.pi / 2))
           for a in [k * math.pi / 8 for k in range(16)]]
    for a in range(16):
        d.line([pts[a], pts[(a + 5) % 16]], fill=EDGE, width=1)
    lit = int(t * 16) % 16
    for k, (x, y) in enumerate(pts):
        on = k == lit
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=ROSE if on else BG,
                  outline=ROSE if on else (0x8A, 0x5A, 0x74), width=2)
    lbl = "25,000 transitive groups"
    d.text((ox - d.textlength(lbl, font=f(UI, 14)) / 2, oy + 98), lbl, font=f(UI, 14), fill=DIM)

    stats(d, 424, [("54 of 256", "final rank"), ("2.3559", "score"),
                   ("10,180", "scoreable pairs"), ("155,366", "pairs already claimed")])
    d.text((M, 534), "Scoring falls off exponentially with how many teams hold a pair.",
           font=f(UI, 16), fill=ROSE)
    foot(d, "IGP24  \u00b7  closed 15 August 2026")
    return im


def modular(i):
    t = i / FRAMES
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    head(im, d, "Modular Arithmetic",
         "Can a network learn exact (a \u00d7 b) mod p, rather than approximate it?")

    def wrap(n, per=30):
        s = str(n)
        return [s[k:k + per] for k in range(0, len(s), per)]

    y = 206
    for lab, val in (("a", MA), ("b", MB), ("p", MP)):
        d.text((M, y + 4), f"{lab} =", font=f(MONO, 16), fill=ROSE)
        for k, ln in enumerate(wrap(val)):
            d.text((M + 48, y + k * 21), ln, font=f(MONO, 16), fill=INK if k == 0 else DIM)
        y += 62

    ox = 566
    layers = [(ox, [290, 356]), (ox + 92, [256, 322, 388]), (ox + 184, [290, 356])]
    for (x1, ys1), (x2, ys2) in zip(layers, layers[1:]):
        for y1 in ys1:
            for y2 in ys2:
                ph = (math.sin(t * math.pi * 2 + (y1 + y2) * 0.03) + 1) / 2
                d.line([x1, y1, x2, y2], fill=(0x5A + int(0x40 * ph), 0x28, 0x48), width=1)
    for x, ys in layers:
        for yy in ys:
            d.ellipse([x - 11, yy - 11, x + 11, yy + 11], fill=BG, outline=INK, width=2)

    panel(d, [820, 208, W - M, 398], active=True)
    d.text((840, 224), "r = (a \u00d7 b) mod p", font=f(MONO, 15), fill=DIM)
    res = str(MR)
    known = int(len(res) * min(1.0, t * 1.5))
    for k in range(0, len(res), 20):
        chunk = "".join(res[j] if j < known else "\u00b7"
                        for j in range(k, min(k + 20, len(res))))
        d.text((840, 258 + (k // 20) * 26), chunk, font=f(MONO, 17), fill=INK)
    d.text((840, 356), "exact match, or nothing", font=f(UI, 14), fill=ROSE)

    stats(d, 424, [("60 digits", "each operand"), ("prime", "the modulus p"),
                   ("130", "teams"), ("exact", "the only passing answer")])
    d.text((M, 534), "Everything arrives as decimal strings, far beyond a 64-bit integer.",
           font=f(UI, 16), fill=ROSE)
    foot(d, "Modular Arithmetic Challenge  \u00b7  closed 12 August 2026")
    return im


def stage1(i):
    t = i / FRAMES
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    head(im, d, "Mathematics Distillation \u00b7 Stage 1",
         "Can mathematical reasoning be compressed into a page a model reads first?")
    pipeline(d, t, [("magma_cheatsheet.md", "2.81 KB written, 10 KB allowed"),
                    ("language model", "temperature 0, seed 0"),
                    ("true  /  false", "one answer per problem")])

    d.text((M, 348), "cheatsheet budget used", font=f(UI, 13), fill=DIM)
    d.rounded_rectangle([M, 374, W - M, 396], radius=6, fill=PANEL, outline=EDGE)
    fillw = int((W - 2 * M) * 0.281)
    d.rounded_rectangle([M, 374, M + fillw, 396], radius=6, fill=ROSE)
    d.text((M + fillw + 14, 375), "2.81 KB of 10 KB", font=f(MONO, 14), fill=PALE)

    stats(d, 424, [("235", "rank"), ("53.5%", "accuracy"), ("41.0%", "F1"),
                   ("100%", "parse rate"), ("$0.00040", "cost per problem")])
    d.text((M, 534), "A model that always answers the same way scores 50 per cent, so accuracy alone proves nothing.",
           font=f(UI, 16), fill=ROSE)
    foot(d, "Equational Theories, Stage 1  \u00b7  closed 20 April 2026")
    return im


def stage2(i):
    t = i / FRAMES
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    head(im, d, "Mathematics Distillation \u00b7 Stage 2",
         "An answer is worth nothing unless it carries a proof a machine will check")
    pipeline(d, t, [("solver.py", "500 KB, deterministic first"),
                    ("Lean 4 certificate", "emitted for each goal"),
                    ("judge", "accepted, or rejected")])

    panel(d, [M, 346, W - M, 452])
    d.text((M + 20, 358), "the shape of a goal the solver closes", font=f(UI, 13), fill=DIM)
    for k, ln in enumerate(["theorem eq (G : Type) (op : G \u2192 G \u2192 G)",
                            "    (h : \u2200 x y, op x y = op y x) : \u2200 x y, op x y = op y x := by"]):
        d.text((M + 20, 384 + k * 24), ln, font=f(MONO, 15), fill=PALE)
    d.text((M + 20, 424), "  intro x y" + " \u00b7" * (int(t * 4) % 4), font=f(MONO, 15), fill=ROSE)

    stats(d, 476, [("500 KB", "solver budget"), ("Lean 4", "certificate"),
                   ("deterministic", "the judge"), ("31 Aug 2026", "Stage 2 closes")])
    foot(d, "Equational Theories, Stage 2")
    return im


BUILDS = {"igp24.gif": igp24}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in BUILDS.items():
        frames = [fn(i).convert("P", palette=Image.ADAPTIVE, colors=64) for i in range(FRAMES)]
        p = out / name
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=MS, loop=0,
                       optimize=False, disposal=2)
        print(f"  {name}: {p.stat().st_size // 1024} KB, {FRAMES} frames")
