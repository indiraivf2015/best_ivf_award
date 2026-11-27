"""Turn the official World Mental Health Day artwork into Creative Studio templates.

The official JPGs carry a grey person icon inside a hand-drawn ring. That ring
is not round -- it is a few pixels wider than it is tall and wobbles -- so a
round photo dropped into it looks off-centre. This script:

  1. fits a circle to the coral ring that is printed on the artwork,
  2. draws a mathematically perfect white band + coral ring over it, sized to
     swallow the old ring completely,
  3. punches a transparent hole inside the band, where the photo goes,
  4. puts the name card back on top: on both layouts the card overlaps the
     bottom of the circle, so it must sit above the ring and close the hole,
  5. saves a copy of the card with "[Doctor Name]" / "Doctor" painted out,
     which the studio pastes in once someone types a name.

Everything runs in the artwork's own pixels, so the numbers printed at the end
paste straight into PRESETS in Indira_Creative_Studio.html. Run from the repo
root:

    python tools/prepare_templates.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SRC = Path.home() / "Downloads"
OUT = Path(__file__).resolve().parent.parent / "templates"

RING = (236, 138, 128)      # coral sampled off the printed ring
BAND = (254, 253, 252)      # white band between the photo and the ring
SS = 4                      # supersample factor for every curved edge

# Per layout, in native pixels of the official artwork:
#   seed  -- rough centre of the printed ring, only used to find it
#   card  -- the name card's rounded rectangle (x0, y0, x1, y1, corner radius)
#   wipe  -- the part of the card holding the placeholder text; stops above
#            the coral underline, which stays
#   ring  -- outer radius of the new coral ring; must clear the old ring's
#            widest point (the script checks)
LAYOUTS = {
    "doctor": dict(
        src="Mental Health Day Doctor creative.jpeg",
        seed=(909, 482),
        card=(690, 701, 1140, 833, 22),
        wipe=(700, 714, 1130, 810),
        ring=225,
    ),
    "counsellor": dict(
        src="Mental Health Day Consellor creative.jpeg",
        seed=(335, 374),
        card=(84, 548, 549, 668, 22),
        wipe=(94, 558, 539, 649),
        ring=235,
    ),
}
RING_W = 6                  # coral ring thickness
BAND_W = 9                  # white band thickness; the hole sits inside it


def fit_ring(a, seed):
    """Least-squares circle through the coral pixels of the printed ring."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    coral = (r > 200) & (r - g > 70) & (r - b > 75)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    near = coral & (np.hypot(xx - seed[0], yy - seed[1]) > 180) & (np.hypot(xx - seed[0], yy - seed[1]) < 250)
    ys, xs = np.nonzero(near)
    # The flower and leaves beside the counsellor's ring are the same coral,
    # so refit a few times, dropping whatever sits well off the last circle.
    for _ in range(4):
        A = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]
        cx, cy, c = np.linalg.lstsq(A, xs ** 2 + ys ** 2, rcond=None)[0]
        d = np.hypot(xs - cx, ys - cy)
        r = np.sqrt(c + cx ** 2 + cy ** 2)
        keep = np.abs(d - r) < 9
        xs, ys, d = xs[keep], ys[keep], d[keep]
    return cx, cy, d.max()


def soft_mask(size, draw):
    """Antialiased L-mode mask: draw() paints at SS x scale, then downsample."""
    w, h = size
    m = Image.new("L", (w * SS, h * SS), 0)
    draw(ImageDraw.Draw(m), SS)
    return np.asarray(m.resize((w, h), Image.LANCZOS)).astype(float) / 255


def disc(cx, cy, r):
    return lambda d, s: d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=255)


def card_shape(x0, y0, x1, y1, rad):
    return lambda d, s: d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=rad * s, fill=255)


def wipe_text(px, box):
    """Paint the placeholder text out: each row blends the card colour found
    just left and right of the text. The card is a near-flat pink, so this
    leaves no trace of the letters or their soft halo."""
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        left = np.median(px[y, x0 - 6:x0], axis=0)
        right = np.median(px[y, x1:x1 + 6], axis=0)
        t = np.linspace(0, 1, x1 - x0)[:, None]
        px[y, x0:x1] = left + (right - left) * t


def build(key, spec):
    src = Image.open(SRC / spec["src"]).convert("RGB")
    orig = np.asarray(src).astype(float)
    size = src.size

    cx, cy, old_r = fit_ring(orig, spec["seed"])
    r_ring = spec["ring"]
    assert r_ring >= old_r + 1.5, f"{key}: ring {r_ring} does not clear the old ring ({old_r:.1f})"
    r_band = r_ring - RING_W
    r_hole = r_band - BAND_W

    ring = soft_mask(size, disc(cx, cy, r_ring))
    band = soft_mask(size, disc(cx, cy, r_band))
    hole = soft_mask(size, disc(cx, cy, r_hole))
    card = soft_mask(size, card_shape(*spec["card"]))

    out = orig.copy()
    out = out * (1 - ring[..., None]) + np.array(RING) * ring[..., None]
    out = out * (1 - band[..., None]) + np.array(BAND) * band[..., None]
    out = out * (1 - card[..., None]) + orig * card[..., None]   # card on top
    alpha = 1 - hole * (1 - card)                                  # card closes the hole

    rgba = np.dstack([out, alpha * 255]).round().clip(0, 255).astype("uint8")
    Image.fromarray(rgba, "RGBA").save(OUT / f"{key}-mhd.png", optimize=True)

    x0, y0, x1, y1 = spec["wipe"]
    blank = orig.copy()
    wipe_text(blank, spec["wipe"])
    patch = blank[y0:y1, x0:x1].round().clip(0, 255).astype("uint8")
    Image.fromarray(patch, "RGB").save(OUT / f"{key}-mhd-card.png", optimize=True)

    cx0, _, cx1, _, _ = spec["card"]
    print(f"{key}: {size[0]}x{size[1]}  old ring r<={old_r:.1f}")
    print(f"  ellipse: [{cx - r_hole:.1f}, {cy - r_hole:.1f}, {cx + r_hole:.1f}, {cy + r_hole:.1f}]")
    print(f"  card patch at ({x0}, {y0})  text centre x={(cx0 + cx1) / 2:.0f}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for key, spec in LAYOUTS.items():
        build(key, spec)
