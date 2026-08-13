# Dome Calculator

A small Flask web app for calculating the geometry of dome structures —
inspired by the [Monolithic Dome Institute's calculators](https://monolithicdome.com/calculators).

Pick a shape from the card grid; each has its own inputs and outputs, all
verified against the reference site's published examples:

- **Spherical Section** — diameter, height, optional stem wall
- **Ellipsoid** — half-ellipsoid (oblate or prolate), optional stem wall
- **Vertical Ellipse** — circular base, elliptical cross-section;
  floor can sit above or below the equator
- **Horizontal Ellipse** — elliptical floor plan (ellipsoid lying on
  its side); volume/surface area have no closed form, so they're computed
  by numerical integration, same approach the reference calculator uses
- **Ellipse** — plain 2D ellipse (not a dome): area, circumference, foci
- **Bulk Storage Calculator** — material (with a given angle of repose
  and density) poured into a dome; computes how it piles up (partly filling
  the structure, partly forming a freestanding cone under the dome ceiling)
  and the resulting storage capacity. An optional Freeboard input holds the
  pile's peak a deliberate clearance below the dome's apex.
- **Bulk Product Storage Sizer** — the inverse problem: given a target
  capacity, angle of repose, and stem wall height, solves via numerical
  root-finding for the hemisphere dome size needed to store it (also
  supports Freeboard)
- **Live & Dead Storage** — reclaim geometry: gravity discharge through a
  floor hopper opening develops a funnel-flow channel at the drawdown
  angle; material inside the channel is live (flows on its own), the rest
  is dead. Outputs live/dead volume and mass, live share, an optional
  required-live check with margin, and an opening-size sensitivity table,
  plus a shaded live/dead section and a plan heatmap of live column depth.
  The engine accepts multiple hopper openings (inline rows, multiple
  tunnels); the UI currently exposes a single centered opening.

All 7 calculators from the reference site are now implemented. Not
included: the "Dome Price" cost estimate shown on the reference site, since
that's an opaque business estimate with no disclosed formula.

## Running it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5050 in your browser.

## Running tests

```bash
source .venv/bin/activate
pip install pytest
python -m pytest
```
