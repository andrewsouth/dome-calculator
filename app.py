from flask import Flask, render_template, request

from geometry import (
    dry_bulk_storage_dome,
    dry_bulk_storage_sizer,
    ellipse,
    ellipsoid_dome,
    horizontal_ellipsoid_dome,
    spherical_dome,
    vertical_ellipsoid_dome,
)

app = Flask(__name__)

UNIT_CHOICES = ["ft", "in", "m", "mm"]
DENSITY_UNIT_CHOICES = [("lbs/ft3", "lbs/ft³"), ("kg/m3", "kg/m³"), ("t/m3", "t/m³")]
WEIGHT_UNIT_CHOICES = [("ton", "ton"), ("lbs", "lbs"), ("tonne", "tonne"), ("kg", "kg"), ("bu", "bu")]


def number_field(key, label, default):
    return {"key": key, "label": label, "default": default, "kind": "number", "unit": "length"}


def plain_number_field(key, label, default, suffix=""):
    return {"key": key, "label": label, "default": default, "kind": "number", "unit": suffix}


def select_field(key, label, default, choices):
    return {"key": key, "label": label, "default": default, "kind": "select", "choices": choices}


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


def _validate_ellipse(v):
    errors = []
    if v["major"] <= 0:
        errors.append("Major radius must be greater than 0.")
    if v["minor"] <= 0:
        errors.append("Minor radius must be greater than 0.")
    return errors


def _validate_dry_bulk_calculator(v):
    errors = []
    if v["diameter"] <= 0:
        errors.append("Diameter must be greater than 0.")
    if v["height"] <= 0:
        errors.append("Height must be greater than 0.")
    elif v["height"] > v["diameter"]:
        errors.append("Height must be no more than the diameter.")
    if v["stem_wall"] < 0:
        errors.append("Stem wall height cannot be negative.")
    if not (0 < v["angle"] < 90):
        errors.append("Angle of repose must be between 0 and 90 degrees.")
    if v["density"] <= 0:
        errors.append("Density must be greater than 0.")
    if v["freeboard"] < 0:
        errors.append("Freeboard cannot be negative.")
    return errors


def _validate_dry_bulk_sizer(v):
    errors = []
    if not (0 < v["angle"] < 90):
        errors.append("Angle of repose must be between 0 and 90 degrees.")
    if v["density"] <= 0:
        errors.append("Density must be greater than 0.")
    if v["capacity"] <= 0:
        errors.append("Capacity must be greater than 0.")
    if v["stem_wall"] < 0:
        errors.append("Stem wall height cannot be negative.")
    if v["freeboard"] < 0:
        errors.append("Freeboard cannot be negative.")
    return errors


SHAPES = {
    "spherical": {
        "label": "Spherical Dome",
        "fields": [
            number_field("diameter", "Diameter", 105.0),
            number_field("height", "Height", 35.0),
            number_field("stem_wall", "Stem Wall", 0.0),
        ],
        "validate": _validate_spherical,
        "compute": lambda v: spherical_dome(v["diameter"], v["height"], v["stem_wall"]),
    },
    "ellipsoid": {
        "label": "Ellipsoid Dome",
        "fields": [
            number_field("diameter", "Diameter", 50.0),
            number_field("height", "Height", 20.0),
            number_field("stem_wall", "Stem Wall", 0.0),
        ],
        "validate": _validate_ellipsoid,
        "compute": lambda v: ellipsoid_dome(v["diameter"], v["height"], v["stem_wall"]),
    },
    "vertical_ellipsoid": {
        "label": "Vertical Ellipsoid Dome",
        "fields": [
            number_field("horizontal", "Horizontal", 25.0),
            number_field("vertical", "Vertical", 16.5),
            number_field("height", "Height", 20.0),
        ],
        "validate": _validate_vertical_ellipsoid,
        "compute": lambda v: vertical_ellipsoid_dome(v["horizontal"], v["vertical"], v["height"]),
    },
    "horizontal_ellipsoid": {
        "label": "Horizontal Ellipsoid Dome",
        "fields": [
            number_field("major", "Major", 25.0),
            number_field("minor", "Minor", 16.5),
            number_field("height", "Height", 20.0),
        ],
        "validate": _validate_horizontal_ellipsoid,
        "compute": lambda v: horizontal_ellipsoid_dome(v["major"], v["minor"], v["height"]),
    },
    "ellipse": {
        "label": "Ellipse",
        "fields": [
            number_field("major", "Major Radius", 30.0),
            number_field("minor", "Minor Radius", 20.0),
        ],
        "validate": _validate_ellipse,
        "compute": lambda v: ellipse(v["major"], v["minor"]),
    },
    "dry_bulk_calculator": {
        "label": "Dry Bulk Storage Calculator",
        "fields": [
            number_field("diameter", "Diameter", 116.0),
            number_field("height", "Height", 58.0),
            number_field("stem_wall", "Stem Wall", 36.0),
            plain_number_field("angle", "Angle of Repose", 32.0, "°"),
            plain_number_field("density", "Density", 50.0),
            select_field("density_unit", "Density Unit", "lbs/ft3", DENSITY_UNIT_CHOICES),
            number_field("freeboard", "Freeboard", 0.0),
        ],
        "validate": _validate_dry_bulk_calculator,
        "compute": lambda v: dry_bulk_storage_dome(
            v["diameter"], v["height"], v["stem_wall"], v["angle"], v["density"], v["density_unit"], v["units"],
            v["freeboard"],
        ),
    },
    "dry_bulk_sizer": {
        "label": "Dry Bulk Storage Sizer",
        "fields": [
            plain_number_field("angle", "Angle of Repose", 32.0, "°"),
            plain_number_field("density", "Density", 50.0),
            select_field("density_unit", "Density Unit", "lbs/ft3", DENSITY_UNIT_CHOICES),
            plain_number_field("capacity", "Capacity", 10000.0),
            select_field("weight_unit", "Capacity Unit", "ton", WEIGHT_UNIT_CHOICES),
            number_field("stem_wall", "Stem Wall", 16.0),
            number_field("freeboard", "Freeboard", 0.0),
        ],
        "validate": _validate_dry_bulk_sizer,
        "compute": lambda v: dry_bulk_storage_sizer(
            v["capacity"], v["weight_unit"], v["density"], v["density_unit"], v["angle"], v["stem_wall"], v["units"],
            v["freeboard"],
        ),
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

    values = {}
    for field in shape["fields"]:
        key = field["key"]
        raw = request.args.get(key)
        if field["kind"] == "select":
            choices = [choice_value for choice_value, _choice_label in field["choices"]]
            values[key] = raw if raw in choices else field["default"]
        else:
            if raw is None:
                values[key] = field["default"]
            else:
                try:
                    values[key] = float(raw.replace(",", ""))
                except ValueError:
                    errors.append(f"'{raw}' is not a valid number for {field['label']}.")
                    values[key] = field["default"]

    units = request.args.get("units", "ft")
    values["units"] = units if units in UNIT_CHOICES else "ft"

    if not errors:
        errors = shape["validate"](values)

    results = None
    if not errors:
        try:
            results = shape["compute"](values)
        except ValueError as error:
            errors.append(str(error))

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
