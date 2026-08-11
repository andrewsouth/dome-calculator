# Dome Calculator

A small Flask web app for calculating the geometry of dome structures —
inspired by the [Monolithic Dome Institute's calculators](https://monolithicdome.com/calculators).

Pick a shape from the dropdown; each has its own inputs and outputs, all
verified against the reference site's published examples:

- **Spherical Dome** — diameter, height, optional stem wall
- **Ellipsoid Dome** — half-ellipsoid (oblate or prolate), optional stem wall
- **Vertical Ellipsoid Dome** — circular base, elliptical cross-section;
  floor can sit above or below the equator
- **Horizontal Ellipsoid Dome** — elliptical floor plan (ellipsoid lying on
  its side); volume/surface area have no closed form, so they're computed
  by numerical integration, same approach the reference calculator uses
- **Ellipse** — plain 2D ellipse (not a dome): area, circumference, foci
- **Dry Bulk Storage Calculator** — material (with a given angle of repose
  and density) poured into a dome; computes how it piles up (partly filling
  the structure, partly forming a freestanding cone under the dome ceiling)
  and the resulting storage capacity. An optional Freeboard input holds the
  pile's peak a deliberate clearance below the dome's apex.
- **Dry Bulk Storage Sizer** — the inverse problem: given a target capacity,
  angle of repose, and stem wall height, solves via numerical root-finding
  for the hemisphere dome size needed to store it (also supports Freeboard)

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
