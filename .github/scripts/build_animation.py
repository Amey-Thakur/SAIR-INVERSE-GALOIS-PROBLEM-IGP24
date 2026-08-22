#!/usr/bin/env python3
"""Build the animated card for this repository.

Original artwork in the palette the repositories already use, so the animation
can live in the repository and be attached to a post without borrowing the
competition site's own canvas. Flat colour throughout, which is what keeps a
1200x630 GIF small enough to post.

    python .github/scripts/build_animation.py .github/assets

Pillow only.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (0x34, 0x08, 0x25)
INK = (0xF5, 0xF5, 0xF5)
DIM = (0xA5, 0x9C, 0xA1)
ROSE = (0xC9, 0xA9, 0xB8)
PALE = (0xD8, 0xD2, 0xD6)
FRAMES, MS = 30, 90

MONO = "C:/Windows/Fonts/consola.ttf"
SEMI = "C:/Windows/Fonts/seguisb.ttf"
UI = "C:/Windows/Fonts/segoeui.ttf"


def f(path, size):
    return ImageFont.truetype(path, size)


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * 2 * t)


def base(title, subtitle):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # SAIR-style stacked triangle mark
    cx, cy = 74, 58
    for i in range(9):
        y = cy - 26 + i * 6
        half = 4 + i * 3.2
        d.rectangle([cx - half, y, cx + half, y + 3], fill=INK)
    d.text((110, 36), "SAIR", font=f(SEMI, 34), fill=INK)
    d.text((60, 108), title, font=f(SEMI, 44), fill=INK)
    d.text((62, 166), subtitle, font=f(UI, 21), fill=DIM)
    d.line([60, 206, W - 60, 206], fill=(0x5A, 0x28, 0x45))
    return im, d


def foot(d, left, right="github.com/Amey-Thakur"):
    d.line([60, H - 74, W - 60, H - 74], fill=(0x5A, 0x28, 0x45))
    d.text((60, H - 58), left, font=f(MONO, 17), fill=DIM)
    w = d.textlength(right, font=f(MONO, 17))
    d.text((W - 60 - w, H - 58), right, font=f(MONO, 17), fill=DIM)


def rounded(d, box, outline, width=2, r=14, fill=None):
    d.rounded_rectangle(box, radius=r, outline=outline, width=width, fill=fill)


# ---------------------------------------------------------------- IGP24
def igp24(i):
    t = i / FRAMES
    im, d = base("Inverse Galois Problem", "Degree 24 over Q. Which finite groups are Galois groups?")
    # polynomial, coefficients cycling
    rounded(d, [60, 236, 470, 384], (0x7A, 0x3A, 0x5C))
    d.text((84, 258), "f(x) = x", font=f(MONO, 24), fill=INK)
    d.text((84 + d.textlength("f(x) = x", font=f(MONO, 24)), 252), "24", font=f(MONO, 15), fill=ROSE)
    coeffs = [(i * 7 + k * 3) % 19 - 9 for k in range(4)]
    txt = "  " + "  ".join(f"{c:+d}x^{23-k}" for k, c in enumerate(coeffs))
    d.text((84, 300), txt[:34], font=f(MONO, 18), fill=PALE)
    d.text((84, 340), "  ... + a\u2081x + a\u2080", font=f(MONO, 18), fill=DIM)
    # arrow
    ax = 490 + int(6 * math.sin(t * math.pi * 2))
    d.line([ax, 310, ax + 90, 310], fill=ROSE, width=3)
    d.polygon([(ax + 90, 302), (ax + 108, 310), (ax + 90, 318)], fill=ROSE)
    # group lattice, nodes lighting in sequence
    ox, oy, R = 800, 310, 96
    pts = [(ox + R * math.cos(a), oy + R * math.sin(a)) for a in
           [k * math.pi / 6 for k in range(12)]]
    for a in range(0, 12, 1):
        for b in range(a + 1, 12, 4):
            d.line([pts[a], pts[b]], fill=(0x6A, 0x30, 0x50), width=1)
    lit = int(t * 12) % 12
    for k, (x, y) in enumerate(pts):
        on = k == lit
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=INK if on else BG,
                  outline=INK if on else (0x8A, 0x5A, 0x74), width=2)
    d.ellipse([ox - 10, oy - 10, ox + 10, oy + 10], fill=ROSE)
    # counter and progress
    n = 1 + int(24999 * t)
    d.text((60, 424), f"24T{n:05d}", font=f(MONO, 26), fill=INK)
    d.text((230, 432), "of 25,000 transitive groups", font=f(UI, 18), fill=DIM)
    d.line([60, 476, W - 60, 476], fill=(0x5A, 0x28, 0x45), width=4)
    d.line([60, 476, 60 + int((W - 120) * t), 476], fill=ROSE, width=4)
    foot(d, "256 teams  \u00b7  closed 15 August 2026")
    return im


# ------------------------------------------------- modular arithmetic
def modular(i):
    t = i / FRAMES
    im, d = base("Modular Arithmetic", "Can a network learn exact (a \u00d7 b) mod p, not approximate it?")
    digits = "8076656417999572913164835284219436314611977"
    rot = lambda s, k: s[k % len(s):] + s[:k % len(s)]
    for k, (lab, col) in enumerate((("a", INK), ("b", PALE), ("p", ROSE))):
        y = 244 + k * 62
        d.text((60, y), f"{lab} =", font=f(MONO, 20), fill=col)
        d.text((110, y), rot(digits, i * 3 + k * 11)[:26] + "\u2026", font=f(MONO, 20), fill=DIM)
    # network, pulsing
    ox = 560
    layers = [(ox, [300, 360]), (ox + 110, [270, 330, 390]), (ox + 220, [300, 360])]
    for (x1, ys1), (x2, ys2) in zip(layers, layers[1:]):
        for y1 in ys1:
            for y2 in ys2:
                ph = (math.sin(t * math.pi * 2 + (y1 + y2) * 0.02) + 1) / 2
                g = int(0x5A + 0x50 * ph)
                d.line([x1, y1, x2, y2], fill=(g, 0x30 + int(0x20 * ph), 0x50), width=1)
    for x, ys in layers:
        for y in ys:
            d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=BG, outline=INK, width=2)
    # exact result resolving left to right
    rounded(d, [880, 250, 1140, 420], (0x7A, 0x3A, 0x5C))
    d.text((900, 268), "r = (a \u00d7 b) mod p", font=f(MONO, 16), fill=DIM)
    res = "2690986462202094854180328297"
    known = int(len(res) * min(1.0, t * 1.4))
    for k in range(0, 28, 14):
        line = "".join(res[j] if j < known else "\u00b7" for j in range(k, min(k + 14, 28)))
        d.text((900, 310 + (k // 14) * 34), line, font=f(MONO, 22), fill=INK if known else DIM)
    d.text((900, 386), "exact match, or nothing", font=f(UI, 15), fill=ROSE)
    foot(d, "130 teams  \u00b7  closed 12 August 2026")
    return im


# ----------------------------------------------------- distillation
def distil(i):
    t = i / FRAMES
    im, d = base("Mathematics Distillation", "An answer is worth nothing unless it carries a proof")
    stages = [("Stage 1", "cheatsheet  10 KB", "language model", "true / false", 244),
              ("Stage 2", "solver.py  500 KB", "Lean 4 certificate", "judge accepts", 400)]
    for si, (name, a, b, c, y) in enumerate(stages):
        active = (t * 2) % 2 >= si and (t * 2) % 2 < si + 1
        col = INK if active else (0x8A, 0x5A, 0x74)
        d.text((60, y - 30), name, font=f(SEMI, 19), fill=ROSE if active else DIM)
        xs = [60, 420, 760]
        labels = [a, b, c]
        for k, (x, lab) in enumerate(zip(xs, labels)):
            wbox = 300 if k < 2 else 320
            rounded(d, [x, y, x + wbox, y + 76], col, 2 if active else 1)
            d.text((x + 18, y + 28), lab, font=f(MONO, 17), fill=col)
            if k < 2:
                prog = max(0.0, min(1.0, ((t * 2) % 2 - si) * 3 - k))
                d.line([x + wbox, y + 38, x + wbox + 40, y + 38], fill=(0x6A, 0x30, 0x50), width=2)
                d.line([x + wbox, y + 38, x + wbox + int(40 * prog), y + 38], fill=ROSE, width=3)
    d.text((60, 512), "Stage 1 rewards a confident answer. Stage 2 removes that.",
           font=f(UI, 18), fill=DIM)
    foot(d, "Stage 2 closes 31 August 2026")
    return im


BUILDS = {"igp24.gif": igp24}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in BUILDS.items():
        frames = [fn(i).convert("P", palette=Image.ADAPTIVE, colors=64) for i in range(FRAMES)]
        p = out / name
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=MS, loop=0,
                       optimize=True, disposal=2)
        print(f"  {name}: {p.stat().st_size // 1024} KB, {FRAMES} frames")
