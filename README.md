# Creative Studio template

A static, in-browser studio that drops a photo and a name / designation onto official campaign artwork, then downloads a PNG.

This build is the **Times Network India Health Awards 2026** studio ("Indira IVF ranked #1 in IVF/Fertility Superclinic Chain Category"), with a single layout for any employee. It started as the World Mental Health Day studio, then Dhanteras, Diwali and Guru Nanak Jayanti 2026. Copy the folder and swap artwork + numbers to reuse it for Diwali, Independence Day, Doctors’ Day, or any other card.

Photos and text stay in the browser. Nothing is uploaded to a server.

## What you get

- Upload one photo, type name / designation / location, download PNG (no Excel / team batch mode)
- One layout (no layout picker)
- Photo fills a perfectly round hole exactly where the cream disc was; the pale gap and thin brown ring stay on top
- The photo can be dragged and zoomed but never pulled off the circle (no transparent gaps)
- The printed cream disc shows until a photo is added
- The printed `Name / Designation / Location` lines show until you type, then that block is swapped for a blank one
- Name, Designation and Location are all required before Download PNG enables

## Run it

Needs Python 3 on the PATH.

```bat
start.bat
```

Or:

```bat
cd "C:\Ganesh Chaturthi_Indira"
python -m http.server 8765
```

Open **http://127.0.0.1:8765/** and hard-refresh after you edit the HTML.

`index.html` redirects to `Indira_Creative_Studio.html`.

## Files

| Path | Role |
|---|---|
| `Indira_Creative_Studio.html` | Whole app (UI + canvas) |
| `index.html` | Redirect into the studio |
| `artwork/times-award-employee.jpg` | Original Times Network award artwork, 4500x4500 (current) |
| `templates/times-award-employee*.png` | 2250x2250 artwork with a transparent photo hole, plus `-empty` and `-card` patches |
| `tools/prepare_times_award.py` | Builds the `times-award-*` templates (see below) |
| `artwork/gurunanak-doctor.jpg`, `templates/gurunanak-*.png`, `tools/prepare_gurunanak.py` | Previous Guru Nanak Jayanti campaign, unused by this build |
| `artwork/diwali-*.png`, `templates/diwali-*.png`, `tools/prepare_diwali.py` | Previous Diwali campaign, unused by this build |
| `artwork/dhanteras-*.png`, `templates/dhanteras-*.png`, `tools/prepare_dhanteras.py` | Previous Dhanteras campaign, unused by this build |
| `templates/*-mhd*.png`, `*rakshabandhan*.png`, `tools/prepare_templates.py` | Earlier campaigns, unused by this build |
| `start.bat` | Local server |
| `vercel.json` | Optional host rewrite |

### The Times Network award template

`tools/prepare_times_award.py` scales the 4500 px artwork to 2250 px, fits
circles to the cream disc and the thin brown ring, and checks that both are
round and concentric (they are: fit error 0.27 px and 0.65 px, centres 0.06 px
apart). Because the printed circles are already true, nothing is redrawn. It
repaints a thin band at the disc's edge with the pale gap colour, so no cream
hairline can sit next to the photo, then punches the hole where the disc was
and saves the `-empty` disc and the blank `-card` text block.

The typed text uses **Baloo 2** at 32 px (Name 500, Designation and Location
400), measured from the printed placeholders. The studio loads that font
explicitly before drawing, since no page element uses it.

```bat
python tools/prepare_times_award.py
```

### The Diwali / Dhanteras templates

The Diwali build uses `tools/prepare_diwali.py` on `artwork/diwali-*.png`; it works exactly like the Dhanteras script described below.

The artwork lives in `artwork/` (`dhanteras-doctor.png`, `dhanteras-employee.png`, 1122x1402).
Their gold rings are hand-placed and wobble by 2-3 px, so `tools/prepare_dhanteras.py`:

1. fits a circle to the gold ring,
2. paints out the old ring and redraws it as a perfect circle of the same
   thickness, coloured angle by angle from the original (gradient kept),
3. punches a transparent hole exactly inside it -> `templates/dhanteras-*.png`,
4. saves the original "ADD PHOTO" disc -> `templates/dhanteras-*-empty.png`,
5. saves the name block with the placeholder text painted out -> `templates/dhanteras-*-card.png`.

It prints each layout's `ellipse`, `emptyAt` and `cardAt` for `PRESETS`. Re-run with:

```bat
python tools/prepare_dhanteras.py
```

### The World Mental Health Day templates (previous campaign)

The official artwork (`Mental Health Day Doctor creative.jpeg`, 1198×1313, and
`Mental Health Day Consellor creative.jpeg`, 1178×1335) has a grey person icon
inside a hand-drawn ring. That ring is not round: it is a few pixels wider than
it is tall, and it wobbles. `tools/prepare_templates.py` turns each image into a
studio template:

1. fits a circle to the printed coral ring (refitting to drop the coral flower
   beside the counsellor's ring),
2. draws a perfectly round white band and coral ring over it, big enough to
   cover the old ring completely (the script stops with an error if it doesn't),
3. punches a transparent hole inside the band for the photo,
4. puts the name card back on top. On both layouts the card overlaps the
   bottom of the circle, so the card closes the hole there,
5. saves `*-mhd-card.png`: the card's text area with `[Doctor Name]` /
   `Doctor` painted out, row by row, from the flat pink on either side.

The script prints each layout's `ellipse` and card position to paste into
`PRESETS`. Run it again with:

```bat
python tools/prepare_templates.py
```

It reads the two JPEGs from your `Downloads` folder. Point `SRC` somewhere else if
they live elsewhere.

## Reuse for another campaign

1. Copy this folder. Rename it, for example `Diwali_Template`.
2. Adapt `LAYOUTS` in `tools/prepare_templates.py` to the new artwork and run it.
3. In `Indira_Creative_Studio.html`, change the title, header copy, and `VERSION`.
4. Update `PRESETS` with the new files and geometry.
5. Add matching `<option>` rows in `#layoutSelect`.
6. Add `loc` to a preset only if the artwork prints a location line. The
   Location field and the download gate both depend on it.
7. Run it locally, try a short name and a long name, download a PNG, and check both layouts.

### Geometry (`PRESETS`)

Coordinates are in **native template pixels** of each artwork.

```js
doctor: {
  src: 'templates/doctor-mhd.png',
  card: 'templates/doctor-mhd-card.png', cardAt: [700, 714], // blank card patch + where it goes
  ellipse: [699.8, 273.0, 1119.8, 693.0],  // the photo hole, as printed by the script
  textX: 915, maxW: 410,                   // centre of the card; the font shrinks past maxW
  name: { baseline: 761, size: 44, weight: 700, fill: INK, font: NAMEPLATE_FONT },
  desg: { baseline: 801, size: 31, weight: 500, fill: INK, font: NAMEPLATE_FONT }
}
```

Baselines and sizes come from the printed placeholder text, so typed names sit
exactly where `[Doctor Name]` / `Doctor` were.

### Why the photo bleeds past the hole

`CLIP_BLEED` (1.5px) lets the photo run slightly wider than the hole. The clip
and the hole both have soft edges. If they match exactly, every edge pixel is
partly transparent and a pale hairline shows. The white band is drawn on top and
hides the overrun.

### Branding

| Knob | Where | What to change |
|---|---|---|
| Page title / header | `<title>`, header HTML | Campaign name |
| Theme colours | `:root` `--accent`, `--coral`, `--blush` | Brand |

## How drawing works

1. The photo is cover-scaled and clipped to `ellipse` (plus `CLIP_BLEED`). With
   no photo yet, a grey placeholder figure fills the circle instead.
2. The template is drawn on top. Its hole lets the photo show, and the band, ring and card stay above it.
3. Once a name or designation is typed, the blank card patch is pasted over the printed placeholders.
4. The name (bold navy) and designation are drawn centred on `textX`.
5. The preview scales that native canvas down. Download PNG is full native size.

## Download PNG

The button enables when **photo, name, and designation** are all filled. You can
download again after the first save.

Open the HTML in Chrome (not only an iframe preview) for one-click save. Preview
frames can block downloads.

## Deploy

Static host (Vercel, Netlify, any file server). `vercel.json` already rewrites `/` to the studio.

After deploy, hard-refresh so browsers do not keep an old `Indira_Creative_Studio.html`.
