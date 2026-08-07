from flask import Flask, render_template, request

from geometry import ellipsoid_dome, spherical_dome

app = Flask(__name__)

UNIT_CHOICES = ["ft", "in", "m", "mm"]

SHAPES = {
    "spherical": {
        "label": "Spherical",
        "compute": spherical_dome,
        "max_height": lambda diameter: diameter,  # cap height <= full sphere
        "defaults": {"diameter": 105.0, "height": 35.0, "stem_wall": 0.0},
    },
    "ellipsoid": {
        "label": "Ellipsoid",
        "compute": ellipsoid_dome,
        "max_height": None,  # oblate or prolate, no upper bound tied to diameter
        "defaults": {"diameter": 50.0, "height": 20.0, "stem_wall": 0.0},
    },
}
DEFAULT_SHAPE = "spherical"


@app.route("/")
def index():
    errors = []

    shape_key = request.args.get("shape", DEFAULT_SHAPE)
    if shape_key not in SHAPES:
        shape_key = DEFAULT_SHAPE
    shape = SHAPES[shape_key]

    values = dict(shape["defaults"])
    for key in ("diameter", "height", "stem_wall"):
        raw = request.args.get(key)
        if raw is None:
            continue
        try:
            values[key] = float(raw)
        except ValueError:
            errors.append(f"'{raw}' is not a valid number for {key.replace('_', ' ')}.")

    units = request.args.get("units", "ft")
    values["units"] = units if units in UNIT_CHOICES else "ft"

    if values["diameter"] <= 0:
        errors.append("Diameter must be greater than 0.")
    if values["height"] <= 0:
        errors.append("Height must be greater than 0.")
    elif shape["max_height"] is not None and values["height"] > shape["max_height"](values["diameter"]):
        errors.append("Height must be no more than the diameter.")
    if values["stem_wall"] < 0:
        errors.append("Stem wall height cannot be negative.")

    results = None
    if not errors:
        results = shape["compute"](values["diameter"], values["height"], values["stem_wall"])

    return render_template(
        "index.html",
        shape_key=shape_key,
        shapes=SHAPES,
        values=values,
        unit_choices=UNIT_CHOICES,
        results=results,
        errors=errors,
    )


if __name__ == "__main__":
    # Port 5000 is commonly occupied on macOS by the AirPlay Receiver.
    app.run(debug=True, port=5050)
