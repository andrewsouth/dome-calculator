# Dome Calculator

A small Flask web app for calculating the geometry of dome structures —
inspired by the [Monolithic Dome Institute's calculators](https://monolithicdome.com/calculators).

Currently supports:

- **Spherical dome** — diameter, height, and optional stem wall as inputs;
  outputs floor radius/circumference/area, dome surface area, volume, and
  more.

Planned next: Ellipsoid, Vertical Ellipsoid, Horizontal Ellipsoid, Ellipse,
and the two Dry Bulk Storage calculators, selectable from the same page.

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
