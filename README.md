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

Planned next: the two Dry Bulk Storage calculators.

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
