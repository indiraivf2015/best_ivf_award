"""Turn the Times Network India Health Awards 2026 artwork into Creative
Studio templates.

The artwork (4500x4500) has, bottom left, a cream disc inside a pale gap and
a thin brown ring, with a "Name / Designation / Location" block under it.
Unlike earlier campaigns the disc and ring are already true circles (fit std
under 1 px) and concentric, so nothing is redrawn. This script:

  1. scales the artwork to WORK px (plenty for social, light for the browser),
  2. fits a circle to the edge of the cream disc (the photo replaces it) and
     to the thin ring (sanity check: both must share a centre),
  3. repaints a thin band around the disc edge with the pale gap colour,
     copied along each ray from just inside the ring, so no cream hairline
     can survive next to the photo,
  4. punches a transparent, antialiased hole exactly where the disc was,
  5. saves a crop of the original cream disc, shown until a photo is added,
  6. saves the text block with the placeholder lines painted out.

All numbers are WORK-scale pixels and print at the end for PRESETS in
Indira_Creative_Studio.html. Run from the repo root:

    python tools/prepare_times_award.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "artwork"
OUT = ROOT / "templates"
WORK = 2250                 # output size (square)
SS = 4                      # supersample factor for curved edges
FEATHER = 5                 # rows of fade at the top/bottom of the text wipe
SMOOTH = 6                  # rows each side averaged when sampling the text-wipe background

# seed -- rough circle centre at WORK scale, only used to find the circle
# wipe -- box holding the placeholder text (x0, y0, x1, y1)
LAYOUTS = {
    "employee": dict(src="times-award-employee.jpg", seed=(320, 1700), wipe=(215, 1912, 415, 2036)),
}


def fit_circle(xs, ys, tol):
    xs, ys = xs.astype(float), ys.astype(float)
    for _ in range(5):
        A = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]
        cx, cy, c = np.linalg.lstsq(A, xs ** 2 + ys ** 2, rcond=None)[0]
        r = np.sqrt(c + cx ** 2 + cy ** 2)
        dd = np.hypot(xs - cx, ys - cy)
        keep = np.abs(dd - r) < tol
        xs, ys = xs[keep], ys[keep]
    dd = np.hypot(xs - cx, ys - cy)
    return cx, cy, r, float(np.std(dd - r))


def soft_disc(size, cx, cy, r):
    w, h = size
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=255)
    return np.asarray(m.resize((w, h), Image.LANCZOS)).astype(float) / 255


def wipe_text(px, box):
    """Each row blends the background found just left and right of the text,
    feathered top and bottom so the patch has no visible edge."""
    x0, y0, x1, y1 = box
    t = np.linspace(0, 1, x1 - x0)[:, None]
    lefts = np.array([np.median(px[y, x0 - 10:x0], axis=0) for y in range(y0 - SMOOTH, y1 + SMOOTH)])
    rights = np.array([np.median(px[y, x1:x1 + 10], axis=0) for y in range(y0 - SMOOTH, y1 + SMOOTH)])
    ker = np.ones(2 * SMOOTH + 1) / (2 * SMOOTH + 1)
    lefts = np.stack([np.convolve(lefts[:, j], ker, "valid") for j in range(3)], 1)
    rights = np.stack([np.convolve(rights[:, j], ker, "valid") for j in range(3)], 1)
    for i, y in enumerate(range(y0, y1)):
        left, right = lefts[i], rights[i]
        w = min(1.0, (y - y0 + 0.5) / FEATHER, (y1 - y - 0.5) / FEATHER)
        px[y, x0:x1] = px[y, x0:x1] * (1 - w) + (left + (right - left) * t) * w


def build(key, spec):
    src = Image.open(SRC / spec["src"]).convert("RGB").resize((WORK, WORK), Image.LANCZOS)
    orig = np.asarray(src).astype(float)
    size = src.size
    H, W = orig.shape[:2]
    r, g, b = orig[..., 0], orig[..., 1], orig[..., 2]
    yy, xx = np.mgrid[0:H, 0:W]
    sx0, sy0 = spec["seed"]
    d0 = np.hypot(xx - sx0, yy - sy0)

    # Thin brown ring.
    ring = (r - b > 40) & (r < 215) & (d0 > 165) & (d0 < 205)
    rcx, rcy, r_ring, ring_sd = fit_circle(*np.nonzero(ring)[::-1], tol=4)

    # Cream disc: its boundary pixels.
    disc = (b < 223) & (r > 238) & (d0 < 181)
    inner = np.roll(disc, 1, 0) & np.roll(disc, -1, 0) & np.roll(disc, 1, 1) & np.roll(disc, -1, 1)
    edge = disc & ~inner & (d0 > 150)
    cx, cy, r_disc, disc_sd = fit_circle(*np.nonzero(edge)[::-1], tol=3)

    off = np.hypot(cx - rcx, cy - rcy)
    if disc_sd > 1.0 or ring_sd > 1.5 or off > 1.0:
        raise SystemExit(f"{key}: circles not clean (disc sd {disc_sd:.2f}, ring sd {ring_sd:.2f}, offset {off:.2f})")

    d = np.hypot(xx - cx, yy - cy)
    th = np.arctan2(yy - cy, xx - cx)
    out = orig.copy()

    # Repaint the disc edge with the gap colour: take each pixel from the
    # middle of the gap (between disc and ring) along the same ray.
    r_gap = (r_disc + (r_ring - 2.5)) / 2
    zone = (d > r_disc - 3) & (d < r_gap)
    gx = np.clip(np.round(cx + r_gap * np.cos(th[zone])).astype(int), 0, W - 1)
    gy = np.clip(np.round(cy + r_gap * np.sin(th[zone])).astype(int), 0, H - 1)
    out[zone] = orig[gy, gx]

    # Hole where the disc was.
    hole = soft_disc(size, cx, cy, r_disc)
    rgba = np.dstack([out, (1 - hole) * 255]).round().clip(0, 255).astype("uint8")
    Image.fromarray(rgba, "RGBA").save(OUT / f"times-award-{key}.png", optimize=True)

    # Original cream disc, shown until a photo is added.
    e0, e1 = int(cx - r_disc - 2), int(cy - r_disc - 2)
    e2, e3 = int(np.ceil(cx + r_disc + 2)), int(np.ceil(cy + r_disc + 2))
    Image.fromarray(orig[e1:e3, e0:e2].round().astype("uint8"), "RGB").save(
        OUT / f"times-award-{key}-empty.png", optimize=True)

    # Blank text block.
    x0, y0, x1, y1 = spec["wipe"]
    blank = out.copy()
    wipe_text(blank, spec["wipe"])
    patch = blank[y0:y1, x0:x1].round().clip(0, 255).astype("uint8")
    Image.fromarray(patch, "RGB").save(OUT / f"times-award-{key}-card.png", optimize=True)

    print(f"{key}: {W}x{H}  disc c=({cx:.2f}, {cy:.2f}) r={r_disc:.2f} (sd {disc_sd:.2f})"
          f"  ring r={r_ring:.2f} (sd {ring_sd:.2f}, offset {off:.2f})")
    print(f"  ellipse: [{cx - r_disc:.1f}, {cy - r_disc:.1f}, {cx + r_disc:.1f}, {cy + r_disc:.1f}]")
    print(f"  emptyAt: [{e0}, {e1}]  cardAt: [{x0}, {y0}]  text centre x={cx:.1f}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for key, spec in LAYOUTS.items():
        build(key, spec)
