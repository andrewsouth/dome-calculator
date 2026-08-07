from flask import Flask, render_template, request

from geometry import ellipsoid_dome, horizontal_ellipsoid_dome, spherical_dome, vertical_ellipsoid_dome

app = Flask(__name__)

UNIT_CHOICES = ["ft", "in", "m", "mm"]


def _validate_spherical(v):
    errors = []
    if v["diameter"] <= 0:
        errors.append("Diameter must be greater than 0.")
    if v["height"] <= 0:
        errors.append("Height must be greater than 0.")
    elif v["height"] > v["diameter"]:
        errors.append("Height must be no more than the diameter.")
    if v["stem_wall"] < 0:
        errors.append("Stem wall height cannot be negative.")
    return errors


def _validate_ellipsoid(v):
    errors = []
    if v["diameter"] <= 0:
        errors.append("Diameter must be greater than 0.")
    if v["height"] <= 0:
        errors.append("Height must be greater than 0.")
    if v["stem_wall"] < 0:
        errors.append("Stem wall height cannot be negative.")
    return errors


def _validate_vertical_ellipsoid(v):
    errors = []
    if v["horizontal"] <= 0:
        errors.append("Horizontal radius must be greater than 0.")
    if v["vertical"] <= 0:
        errors.append("Vertical radius must be greater than 0.")
    elif v["height"] <= 0 or v["height"] >= 2 * v["vertical"]:
        errors.append("Height must be greater than 0 and less than twice the vertical radius.")
    return errors


def _validate_horizontal_ellipsoid(v):
    errors = []
    if v["major"] <= 0:
        errors.append("Major radius must be greater than 0.")
    if v["minor"] <= 0:
        errors.append("Minor radius must be greater than 0.")
    elif v["height"] <= 0 or v["height"] >= 2 * v["minor"]:
        errors.append("Height must be greater than 0 and less than twice the minor radius.")
    return errors


SHAPES = {
    "spherical": {
        "label": "Spherical",
        "fields": [
            ("diameter", "Diameter", 105.0),
            ("height", "Height", 35.0),
            ("stem_wall", "Stem Wall", 0.0),
        ],
        "validate": _validate_spherical,
        "compute": lambda v: spherical_dome(v["diameter"], v["height"], v["stem_wall"]),
    },
    "ellipsoid": {
        "label": "Ellipsoid",
        "fields": [
            ("diameter", "Diameter", 50.0),
            ("height", "Height", 20.0),
            ("stem_wall", "Stem Wall", 0.0),
        ],
        "validate": _validate_ellipsoid,
        "compute": lambda v: ellipsoid_dome(v["diameter"], v["height"], v["stem_wall"]),
    },
    "vertical_ellipsoid": {
        "label": "Vertical Ellipsoid",
        "fields": [
            ("horizontal", "Horizontal", 25.0),
            ("vertical", "Vertical", 16.5),
            ("height", "Height", 20.0),
        ],
        "validate": _validate_vertical_ellipsoid,
        "compute": lambda v: vertical_ellipsoid_dome(v["horizontal"], v["vertical"], v["height"]),
    },
    "horizontal_ellipsoid": {
        "label": "Horizontal Ellipsoid",
        "fields": [
            ("major", "Major", 25.0),
            ("minor", "Minor", 16.5),
            ("height", "Height", 20.0),
        ],
        "validate": _validate_horizontal_ellipsoid,
        "compute": lambda v: horizontal_ellipsoid_dome(v["major"], v["minor"], v["height"]),
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

    values = {key: default for key, _label, default in shape["fields"]}
    for key in values:
        raw = request.args.get(key)
        if raw is None:
            continue
        try:
            values[key] = float(raw)
        except ValueError:
            errors.append(f"'{raw}' is not a valid number for {key.replace('_', ' ')}.")

    units = request.args.get("units", "ft")
    values["units"] = units if units in UNIT_CHOICES else "ft"

    if not errors:
        errors = shape["validate"](values)

    results = None
    if not errors:
        results = shape["compute"](values)

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
