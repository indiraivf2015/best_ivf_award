"""Turn the Dhanteras artwork into Creative Studio templates.

Each artwork has a gold ring with a grey "ADD PHOTO" disc inside it, and a
"Dr. Name / Designation / Location" (or "Employee Name / ...") block under it.
The rings are hand-placed and wobble by 2-3 px, so a round photo dropped in
would leave grey slivers on one side and bite the gold on the other. This
script:

  1. fits a circle to the gold ring printed on the artwork,
  2. paints out the old ring and redraws it as a perfect circle of the same
     thickness, coloured angle by angle from the original so the gold
     gradient and highlights survive,
  3. punches a transparent hole exactly inside the new ring (the photo goes
     there; the studio draws it underneath),
  4. saves a crop of the original "ADD PHOTO" disc, shown until a photo is
     added,
  5. saves the text block with the placeholder lines painted out, which the
     studio pastes in once someone types.

All numbers are native artwork pixels and print at the end for PRESETS in
Indira_Creative_Studio.html. Run from the repo root:

    python tools/prepare_dhanteras.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "artwork"
OUT = ROOT / "templates"
SS = 4                      # supersample factor for curved edges
FEATHER = 5                 # rows of fade at the top/bottom of the text wipe

# seed -- rough ring centre, only used to find the ring
# wipe -- box holding the placeholder text (x0, y0, x1, y1), clear of the ring
LAYOUTS = {
    "doctor": dict(src="dhanteras-doctor.png", seed=(857, 953), wipe=(770, 1160, 958, 1284)),
    "employee": dict(src="dhanteras-employee.png", seed=(258, 1018), wipe=(108, 1197, 408, 1322)),
}


def gold_mask(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r - b > 60) & (r > 150) & (g > 90)


def fit_ring(a, seed):
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    d = np.hypot(xx - seed[0], yy - seed[1])
    ys, xs = np.nonzero(gold_mask(a) & (d > 140) & (d < 215))
    for _ in range(4):
        A = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]
        cx, cy, c = np.linalg.lstsq(A, xs ** 2 + ys ** 2, rcond=None)[0]
        r = np.sqrt(c + cx ** 2 + cy ** 2)
        dd = np.hypot(xs - cx, ys - cy)
        keep = np.abs(dd - r) < 6
        xs, ys, dd = xs[keep], ys[keep], dd[keep]
    ang = np.arctan2(ys - cy, xs - cx)
    bins = np.linspace(-np.pi, np.pi, 73)
    inner, outer = [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        s = (ang >= lo) & (ang < hi)
        if s.any():
            inner.append(dd[s].min())
            outer.append(dd[s].max())
    return cx, cy, np.mean(inner), np.mean(outer), min(inner), max(outer)


def soft_disc(size, cx, cy, r):
    w, h = size
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=255)
    return np.asarray(m.resize((w, h), Image.LANCZOS)).astype(float) / 255


def ring_colours(a, cx, cy, r_lo, r_hi, n=720):
    """Per-angle colour of the printed ring: the most saturated gold pixel on
    each ray, smoothed over a couple of degrees."""
    cols = np.zeros((n, 3))
    for i in range(n):
        t = -np.pi + 2 * np.pi * (i + 0.5) / n
        best = []
        for r in np.arange(r_lo, r_hi, 0.5):
            x, y = int(round(cx + r * np.cos(t))), int(round(cy + r * np.sin(t)))
            p = a[y, x]
            best.append((p[0] - p[2], tuple(p)))
        best.sort(reverse=True)
        cols[i] = np.mean([p for _, p in best[:2]], axis=0)
    k = 5
    pad = np.concatenate([cols[-k:], cols, cols[:k]])
    ker = np.ones(2 * k + 1) / (2 * k + 1)
    return np.stack([np.convolve(pad[:, j], ker, "valid") for j in range(3)], 1)


def wipe_text(px, box):
    """Each row blends the background found just left and right of the text.
    The top and bottom FEATHER rows (above and below the text) fade back into
    the original, so the patch has no visible edge."""
    x0, y0, x1, y1 = box
    t = np.linspace(0, 1, x1 - x0)[:, None]
    for y in range(y0, y1):
        left = np.median(px[y, x0 - 6:x0], axis=0)
        right = np.median(px[y, x1:x1 + 6], axis=0)
        w = min(1.0, (y - y0 + 0.5) / FEATHER, (y1 - y - 0.5) / FEATHER)
        px[y, x0:x1] = px[y, x0:x1] * (1 - w) + (left + (right - left) * t) * w


def build(key, spec):
    src = Image.open(SRC / spec["src"]).convert("RGB")
    orig = np.asarray(src).astype(float)
    size = src.size
    H, W = orig.shape[:2]

    cx, cy, r_in, r_out, in_min, out_max = fit_ring(orig, spec["seed"])
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot(xx - cx, yy - cy)
    th = np.arctan2(yy - cy, xx - cx)

    out = orig.copy()

    # 1. Paint out the old ring's outside wobble: copy each pixel from just
    #    beyond the widest point of the old ring, along the same ray.
    r_clear = out_max + 2.5
    zone = (d > r_out - 1) & (d < r_clear + 0.5)
    sx = np.clip(np.round(cx + (r_clear + 1.5) * np.cos(th[zone])).astype(int), 0, W - 1)
    sy = np.clip(np.round(cy + (r_clear + 1.5) * np.sin(th[zone])).astype(int), 0, H - 1)
    out[zone] = orig[sy, sx]

    # 2. Redraw a perfect ring of the same thickness, original colours.
    lut = ring_colours(orig, cx, cy, in_min - 1, out_max + 1)
    idx = ((th + np.pi) / (2 * np.pi) * len(lut)).astype(int) % len(lut)
    gold = lut[idx]
    ring = soft_disc(size, cx, cy, r_out)
    out = out * (1 - ring[..., None]) + gold * ring[..., None]

    # 3. Hole inside the ring.
    hole = soft_disc(size, cx, cy, r_in)
    alpha = 1 - hole
    rgba = np.dstack([out, alpha * 255]).round().clip(0, 255).astype("uint8")
    Image.fromarray(rgba, "RGBA").save(OUT / f"dhanteras-{key}.png", optimize=True)

    # 4. "ADD PHOTO" disc, shown until a photo is added.
    e0, e1 = int(cx - r_in - 2), int(cy - r_in - 2)
    e2, e3 = int(np.ceil(cx + r_in + 2)), int(np.ceil(cy + r_in + 2))
    Image.fromarray(orig[e1:e3, e0:e2].round().astype("uint8"), "RGB").save(
        OUT / f"dhanteras-{key}-empty.png", optimize=True)

    # 5. Blank text block.
    x0, y0, x1, y1 = spec["wipe"]
    blank = out.copy()
    wipe_text(blank, spec["wipe"])
    patch = blank[y0:y1, x0:x1].round().clip(0, 255).astype("uint8")
    Image.fromarray(patch, "RGB").save(OUT / f"dhanteras-{key}-card.png", optimize=True)

    print(f"{key}: {W}x{H}  ring c=({cx:.1f}, {cy:.1f})  r {r_in:.1f}..{r_out:.1f}"
          f"  (old wobble {in_min:.1f}..{out_max:.1f})")
    print(f"  ellipse: [{cx - r_in:.1f}, {cy - r_in:.1f}, {cx + r_in:.1f}, {cy + r_in:.1f}]")
    print(f"  empty at [{e0}, {e1}]  card at [{x0}, {y0}]  text centre x={cx:.1f}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for key, spec in LAYOUTS.items():
        build(key, spec)
