# ==============================================================================
# File: build_sair_card.py
# Description: Builds the repository card in the visual language of the SAIR
#   Foundation's hero art for IGP24: a vertical copper to aubergine gradient
#   and white line work, read left to right. The rationals go in, one degree 24
#   polynomial comes out of the funnel, and the Galois group of that polynomial
#   is the graph on the right; underneath runs the ladder of transitive groups
#   the search walks. Laid out directly in card coordinates rather than scaled
#   from the hero, because the hero leaves room for page copy that a repository
#   card does not need. Every element declares a box, and the build asserts that
#   no two boxes intersect.
# Usage: python .github/scripts/build_sair_card.py .github/assets
# Tech Stack: Python 3.10+, Pillow
# ==============================================================================

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 675
SS = 3
FRAMES, DURATION = 30, 60

TOP = (0x8F, 0x57, 0x43)     # sampled from the top row of SAIR's hero
BOT = (0x34, 0x08, 0x25)     # and its bottom row, the SAIR card colour
INK = (255, 255, 255)
STROKE = 4

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
UIB = "C:/Windows/Fonts/segoeuib.ttf"
# Cambria Math is the only face installed here carrying U+211A and U+22EF, so
# the mathematics is set in it rather than approximated in a sans face.
MATH, MATH_IDX = "C:/Windows/Fonts/cambria.ttc", 1

POLY = "f(x) = a\u2080 + a\u2081x + \u22ef + a\u2082\u2084x\u00b2\u2074"

# -- layout -----------------------------------------------------------------
# One place for every position, so the boxes below describe what is drawn.

# The card is built on a 56px margin. Content runs from x 56 to x 1144 and
# from y 44 to y 632, so the left and right margins match and the top and
# bottom margins match. Nothing is placed by eye.

M = 56
LOGO = (M, 44, M + 240, 96)              # x0, y0, x1, y1
Q_C, Q_H = (196, 316), 280
FUNNEL_X = (344, 468)
FUNNEL_Y = (128, 504)
ARROW_X, ARROW_MID, ARROW_HALF = (468, 744), 316, 44
POLY_C, POLY_W, POLY_H = (612, 196), 264, 44
ROOT_C, ROOT_R = (612, 416), 36
GRAPH_C, GRAPH_R, ARC_R = (952, 316), 164, 192
AXIS_Y, AXIS_A, AXIS_B = 582, (150, 660), (850, 1034)
STOPS = ((246, "24T1"), (405, "24T2"), (564, "24T3"))
DOTS = (700, 735, 770, 805)
END_C, END_R = 1060, 26
MAG_C, MAG_R = (86, 582), 26
LABEL_Y = 616

BOXES = {
    "logo": LOGO,
    "rationals": (Q_C[0] - Q_H * 0.47, Q_C[1] - Q_H / 2,
                  Q_C[0] + Q_H * 0.47, Q_C[1] + Q_H / 2),
    "funnel": (FUNNEL_X[0], FUNNEL_Y[0], FUNNEL_X[1], FUNNEL_Y[1]),
    "polynomial": (POLY_C[0] - POLY_W / 2, POLY_C[1] - POLY_H / 2,
                   POLY_C[0] + POLY_W / 2, POLY_C[1] + POLY_H / 2),
    "arrow": (ARROW_X[0], ARROW_MID - ARROW_HALF,
              ARROW_X[1], ARROW_MID + ARROW_HALF),
    "root": (ROOT_C[0] - ROOT_R, ARROW_MID + ARROW_HALF + 6,
             ROOT_C[0] + ROOT_R, ROOT_C[1] + ROOT_R),
    "group": (GRAPH_C[0] - ARC_R, GRAPH_C[1] - ARC_R,
              GRAPH_C[0] + ARC_R, GRAPH_C[1] + ARC_R),
    "ladder": (MAG_C[0] - MAG_R, AXIS_Y - 34, END_C + 66, LABEL_Y + 16),
}


def assert_no_overlap():
    names = list(BOXES)
    bad = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = BOXES[names[i]], BOXES[names[j]]
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > 0 and oy > 0:
                bad.append(f"{names[i]} and {names[j]} overlap by "
                           f"{ox:.0f}x{oy:.0f}")
    if bad:
        raise SystemExit("layout collision: " + "; ".join(bad))
    xs = [v for b in BOXES.values() for v in (b[0], b[2])]
    ys = [v for b in BOXES.values() for v in (b[1], b[3])]
    print(f"  extent x {min(xs):.0f}-{max(xs):.0f}  y {min(ys):.0f}-{max(ys):.0f}")


_scratch = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def f(path, size, index=0):
    return ImageFont.truetype(path, max(1, int(round(size * SS))), index=index)


def fit_width(path, text, target, index=0):
    lo, hi = 4.0, 400.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if _scratch.textlength(text, font=f(path, mid, index)) / SS < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def fit_height(path, text, target, index=0):
    lo, hi = 4.0, 800.0
    for _ in range(40):
        mid = (lo + hi) / 2
        bb = _scratch.textbbox((0, 0), text, font=f(path, mid, index))
        if (bb[3] - bb[1]) / SS < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def bg_at(py):
    t = max(0.0, min(1.0, py / (H - 1.0)))
    return tuple(round(TOP[i] + (BOT[i] - TOP[i]) * t) for i in range(3))


def dim(py, amount):
    b = bg_at(py)
    return tuple(round(b[i] + (INK[i] - b[i]) * amount) for i in range(3))


def ease(t):
    return t * t * (3 - 2 * t)


OFFSET = [0.0, 0.0]          # set once by centre_offset(), then applied to all


class Pen:
    def __init__(self, draw):
        self.d = draw

    def _p(self, pts):
        ox, oy = OFFSET
        return [((p[0] + ox) * SS, (p[1] + oy) * SS) for p in pts]

    def line(self, pts, colour=INK, width=STROKE, joint="curve"):
        if len(pts) < 2:
            return
        self.d.line(self._p(pts), fill=colour,
                    width=int(round(width * SS)), joint=joint)

    def circle(self, cx, cy, r, colour=INK, width=STROKE):
        ox, oy = OFFSET
        self.d.ellipse([(cx + ox - r) * SS, (cy + oy - r) * SS,
                        (cx + ox + r) * SS, (cy + oy + r) * SS],
                       outline=colour, width=int(round(width * SS)))

    def disc(self, cx, cy, r, colour=INK):
        ox, oy = OFFSET
        self.d.ellipse([(cx + ox - r) * SS, (cy + oy - r) * SS,
                        (cx + ox + r) * SS, (cy + oy + r) * SS], fill=colour)

    def dashed_arc(self, cx, cy, r, a0, a1, step, colour=INK, width=STROKE):
        a = a0
        while a < a1:
            ox, oy = OFFSET
            self.d.arc([(cx + ox - r) * SS, (cy + oy - r) * SS,
                        (cx + ox + r) * SS, (cy + oy + r) * SS],
                       a, min(a + step * 0.55, a1),
                       fill=colour, width=int(round(width * SS)))
            a += step

    def text(self, pos, s, font, colour=INK, anchor="la"):
        ox, oy = OFFSET
        self.d.text(((pos[0] + ox) * SS, (pos[1] + oy) * SS), s, font=font,
                    fill=colour, anchor=anchor)


def bezier(p0, p1, p2, p3, n=30):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                    u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]))
    return out


# -- the group, laid out once so only the lighting moves --------------------

NODES = [
    (0.00, 0.00, 9), (0.46, -0.30, 8), (-0.44, -0.22, 7), (0.10, -0.62, 7),
    (-0.20, 0.46, 8), (0.40, 0.38, 7), (-0.62, 0.16, 6), (0.68, 0.04, 6),
    (0.20, 0.72, 6), (-0.34, -0.62, 6), (0.62, -0.60, 6), (-0.70, -0.44, 5),
    (-0.52, 0.60, 5), (0.02, -0.86, 5), (-0.86, -0.10, 5), (0.80, -0.34, 5),
    (0.56, 0.66, 5), (-0.16, 0.86, 5),
]
EDGES = [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 3), (1, 5), (1, 7),
         (2, 3), (2, 6), (2, 9), (3, 9), (3, 13), (4, 5), (4, 6), (4, 8),
         (4, 12), (5, 7), (5, 8), (5, 16), (6, 11), (6, 12), (6, 14),
         (7, 15), (7, 16), (8, 17), (9, 11), (9, 13), (1, 10), (10, 15),
         (11, 14), (12, 17), (13, 3), (16, 8)]


def node_xy(i):
    fx, fy, _ = NODES[i]
    return GRAPH_C[0] + fx * GRAPH_R * 0.82, GRAPH_C[1] + fy * GRAPH_R * 0.82


# -- the drawing ------------------------------------------------------------

def rationals(pen):
    """The rationals, set as the actual character rather than drawn.

    A hand made double struck Q reads as a mistake; this is U+211A, sized to
    the height the symbol has in SAIR's artwork."""
    pen.text(Q_C, "\u211a", MATH_Q, INK, "mm")


def funnel_and_arrow(pen, t):
    """Every polynomial over the rationals narrows to the one submitted.

    The arrow stops short of the group: they are two objects, and drawing them
    touching would say something the mathematics does not."""
    x0, x1 = FUNNEL_X
    top, bot = ARROW_MID - 15, ARROW_MID + 15
    pen.line(bezier((x0, FUNNEL_Y[0]), (x0 + 96, FUNNEL_Y[0] + 8),
                    (x1 - 38, top - 44), (x1, top)))
    pen.line(bezier((x0, FUNNEL_Y[1]), (x0 + 96, FUNNEL_Y[1] - 8),
                    (x1 - 38, bot + 44), (x1, bot)))

    a, tip = ARROW_X
    flare = tip - 58
    pen.line([(a, top), (flare, top), (flare, ARROW_MID - ARROW_HALF),
              (tip, ARROW_MID), (flare, ARROW_MID + ARROW_HALF),
              (flare, bot), (a, bot)])

    u = (t % 1.0) / 0.42
    if u < 1.0:
        px = a + 14 + (flare - 46 - a - 14) * ease(u)
        pen.line([(max(a + 14, px - 62), ARROW_MID), (px, ARROW_MID)],
                 INK, STROKE + 1)

    yy = bot + 10
    while yy < ROOT_C[1] - ROOT_R - 4:
        pen.line([(ROOT_C[0], yy), (ROOT_C[0], min(yy + 11, ROOT_C[1] - ROOT_R - 4))],
                 dim(yy, 0.85), STROKE, None)
        yy += 22
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (t - 0.25))
    pen.circle(ROOT_C[0], ROOT_C[1], ROOT_R, dim(ROOT_C[1], 0.62 + 0.38 * pulse))
    pen.text(ROOT_C, "r", MATH_R, INK, "mm")


def galois_group(pen, t):
    pen.circle(GRAPH_C[0], GRAPH_C[1], GRAPH_R)
    for a, b in EDGES:
        ax, ay = node_xy(a)
        bx, by = node_xy(b)
        pen.line([(ax, ay), (bx, by)], dim(GRAPH_C[1], 0.80), 2)
    for i, (_, _, r) in enumerate(NODES):
        nx, ny = node_xy(i)
        wave = 0.5 + 0.5 * math.sin(2 * math.pi * (t - i * 0.055))
        pen.disc(nx, ny, r * (0.90 + 0.16 * wave), dim(ny, 0.86 + 0.14 * wave))
    for a0 in (-76, 16):
        pen.dashed_arc(GRAPH_C[0], GRAPH_C[1], ARC_R, a0, a0 + 60, 7.5,
                       dim(GRAPH_C[1], 0.9), 3)


def ladder(pen, t):
    """The transitive groups of degree 24. There are exactly 25000 of them, and
    that enumeration is the search space the problem is posed over."""
    pen.circle(MAG_C[0], MAG_C[1] - 6, MAG_R)
    pen.line([(MAG_C[0] + 19, MAG_C[1] + 13), (MAG_C[0] + 34, MAG_C[1] + 28)])

    pen.line([(AXIS_A[0], AXIS_Y), (AXIS_A[1], AXIS_Y)], dim(AXIS_Y, 0.9), 3)
    pen.line([(AXIS_B[0], AXIS_Y), (AXIS_B[1], AXIS_Y)], dim(AXIS_Y, 0.9), 3)
    lit = int(t * 4) % 4
    for i, (px, label) in enumerate(STOPS):
        on = i == lit
        pen.disc(px, AXIS_Y, 15 if on else 13, dim(AXIS_Y, 1.0 if on else 0.55))
        pen.text((px, LABEL_Y), label, TICK, dim(LABEL_Y, 0.75 + 0.25 * on), "mt")
    for k, px in enumerate(DOTS):
        a = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(2 * math.pi * (t - k * 0.08)))
        pen.disc(px, AXIS_Y, 7, dim(AXIS_Y, a))
    on = lit == 3
    pen.circle(END_C, AXIS_Y, END_R, dim(AXIS_Y, 1.0 if on else 0.6))
    pen.text((END_C, LABEL_Y), "24T25000", TICK,
             dim(LABEL_Y, 0.75 + 0.25 * on), "mt")


# -- type -------------------------------------------------------------------

FS_POLY = fit_width(MATH, POLY, POLY_W, MATH_IDX)
MATH_Q = f(MATH, fit_height(MATH, "\u211a", Q_H, MATH_IDX), MATH_IDX)
MATH_R = f(MATH, fit_height(MATH, "r", 26, MATH_IDX), MATH_IDX)
TICK = f(UIB, fit_width(UIB, "24T25000", 132))


def background():
    im = Image.new("RGB", (1, H))
    px = im.load()
    for py in range(H):
        px[0, py] = bg_at(py)
    return im.resize((W * SS, H * SS), Image.BILINEAR)


BG = background()


def logo(im):
    """SAIR's own mark and wordmark, keyed off the gradient they were drawn on
    and recomposited onto ours."""
    art = Image.open(os.path.join(ASSETS, "sair-logo.png")).convert("RGBA")
    w = LOGO[2] - LOGO[0]
    h = round(art.height * (w / art.width))
    art = art.resize((round(w * SS), h * SS), Image.LANCZOS)
    ox, oy = OFFSET
    im.paste(art, (round((LOGO[0] + ox) * SS), round((LOGO[1] + oy) * SS)), art)


def frame(i):
    t = i / FRAMES
    im = BG.copy()
    pen = Pen(ImageDraw.Draw(im))
    logo(im)
    rationals(pen)
    pen.text(POLY_C, POLY, f(MATH, FS_POLY, MATH_IDX), INK, "mm")
    funnel_and_arrow(pen, t)
    galois_group(pen, t)
    ladder(pen, t)
    return im.resize((W, H), Image.LANCZOS)


def check_glyphs():
    missing = set()
    for face, index, lines in ((MATH, MATH_IDX, (POLY, "\u211a", "r")),
                               (UIB, 0, ("24T25000",))):
        font = f(face, 40, index)
        for line in lines:
            for ch in line:
                if ch != " " and font.getmask(ch).getbbox() is None:
                    missing.add((os.path.basename(face), ch))
    if missing:
        raise SystemExit("font is missing glyphs: " + repr(sorted(missing)))


def centre_offset():
    """Measure one probe frame and return the shift that equalises the margins."""
    import numpy as np

    OFFSET[0] = OFFSET[1] = 0.0
    a = np.asarray(frame(0).convert("RGB")).astype(int)
    ink = (a.min(axis=2) > 165) & ((a.max(axis=2) - a.min(axis=2)) < 50)
    cols = np.where(ink.any(axis=0))[0]
    rows = np.where(ink.any(axis=1))[0]
    dx = ((W - 1 - cols.max()) - cols.min()) / 2.0
    dy = ((H - 1 - rows.max()) - rows.min()) / 2.0
    print(f"  centring by ({dx:+.1f}, {dy:+.1f})")
    return dx, dy


def check_layout(im):
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(int)
    ink = (a.min(axis=2) > 165) & ((a.max(axis=2) - a.min(axis=2)) < 50)
    rows = np.where(ink.any(axis=1))[0]
    cols = np.where(ink.any(axis=0))[0]
    left, right = int(cols.min()), int(W - 1 - cols.max())
    top, bottom = int(rows.min()), int(H - 1 - rows.max())
    print(f"  margins  left {left}  right {right}  top {top}  bottom {bottom}")
    used = (cols.max() - cols.min()) * (rows.max() - rows.min()) / (W * H)
    print(f"  the artwork spans {used * 100:.0f}% of the card")
    if min(left, right, top, bottom) < 24:
        raise SystemExit("ink runs too close to an edge")
    if abs(left - right) > 6:
        raise SystemExit(f"card is not symmetric: left {left}, right {right}")
    if abs(top - bottom) > 6:
        raise SystemExit(f"card is not balanced: top {top}, bottom {bottom}")
    if used < 0.74:
        raise SystemExit(f"the card is not using its space ({used*100:.0f}%)")


def quantise(frames):
    """One shared palette, matched exactly. Sharing it makes consecutive frames
    differ only where something moved; matching by hand keeps the gradient
    smooth, which Pillow's approximate matcher does not."""
    import numpy as np

    col = np.asarray(frames[0].convert("RGB")).astype(int)[:, 4, :]
    entries, seen = [], set()
    for c in map(tuple, col):
        if c not in seen:
            seen.add(c)
            entries.append(c)
    for a in (0.45, 0.55, 0.62, 0.72, 0.8, 0.85, 0.9, 0.95):
        for py in (0, H * 0.3, H * 0.55, H * 0.8, H - 1):
            c = dim(py, a)
            if c not in seen:
                seen.add(c)
                entries.append(c)
    if (255, 255, 255) not in seen:
        entries.append((255, 255, 255))
    entries = entries[:256]
    table = [v for c in entries for v in c] + [0, 0, 0] * (256 - len(entries))
    exact = {c: i for i, c in enumerate(entries)}
    arr = np.array(entries, dtype=np.int32)

    out, cache = [], {}
    for fr in frames:
        a = np.asarray(fr.convert("RGB"))
        flat = a.reshape(-1, 3).astype(np.int32)
        keys = (flat[:, 0] << 16) | (flat[:, 1] << 8) | flat[:, 2]
        uniq, inverse = np.unique(keys, return_inverse=True)
        lut = np.empty(len(uniq), dtype=np.uint8)
        for j, k in enumerate(uniq.tolist()):
            c = ((k >> 16) & 255, (k >> 8) & 255, k & 255)
            i = exact.get(c)
            if i is None:
                i = cache.get(c)
                if i is None:
                    i = int(((arr - np.array(c)) ** 2).sum(axis=1).argmin())
                    cache[c] = i
            lut[j] = i
        im = Image.fromarray(lut[inverse].reshape(a.shape[:2]), mode="P")
        im.putpalette(table)
        out.append(im)
    return out


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else ASSETS
    os.makedirs(out, exist_ok=True)
    check_glyphs()
    assert_no_overlap()
    OFFSET[0], OFFSET[1] = centre_offset()
    frames = [frame(i) for i in range(FRAMES)]
    check_layout(frames[0])
    path = os.path.join(out, "igp24-sair.gif")
    q = quantise(frames)
    q[0].save(path, save_all=True, append_images=q[1:], duration=DURATION,
              loop=0, optimize=True, disposal=1)
    print(f"  {os.path.basename(path)}: {os.path.getsize(path) // 1024} KB, "
          f"{len(frames)} frames, {W}x{H}")
