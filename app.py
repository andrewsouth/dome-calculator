from flask import Flask, render_template, request

import diagrams
import drawings
import iso
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
# Freeboard default depends on the selected length unit: 1.5 ft or 0.5 m.
FREEBOARD_DEFAULTS = {"ft": 1.5, "in": 18.0, "m": 0.5, "mm": 500.0}


def number_field(key, label, default):
    return {"key": key, "label": label, "default": default, "kind": "number", "unit": "length"}


def plain_number_field(key, label, default, suffix=""):
    return {"key": key, "label": label, "default": default, "kind": "number", "unit": suffix}


def select_field(key, label, default, choices):
    return {"key": key, "label": label, "default": default, "kind": "select", "choices": choices}


_ICON_STROKE = 'stroke="#444" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"'


def _dome_icon(dome_ry=30, stem_wall=False, pile=False, dashed=False):
    """Ground line + dome arc (radius 30, chord 20..80); optional stem wall,
    dashed outline, and a product pile at a ~30 degree angle of repose."""
    dash = ' stroke-dasharray="5,4"' if dashed else ""
    base_y = 50 if stem_wall else 65
    # Pile with no freeboard: fills against the stem walls and up the dome
    # wall, peaking at the apex. A 30-degree repose line from the apex
    # (50,20) meets the r=30 shell at (50 +- 26, 35), so the outline runs
    # up the wall, along the dome arc to that contact point, then straight
    # to the peak (slope 15/26 = 30 degrees each side).
    pile_svg = (
        '<path d="M20 65 L20 50 A30 30 0 0 1 24 35 L50 20 L76 35 '
        'A30 30 0 0 1 80 50 L80 65 Z" '
        'fill="#ccc" stroke="#444" stroke-width="2" stroke-linejoin="round"/>'
        if pile else ""
    )
    walls_svg = (
        f'<path d="M20 65 L20 50" {_ICON_STROKE}{dash}/>'
        f'<path d="M80 65 L80 50" {_ICON_STROKE}{dash}/>'
        if stem_wall else ""
    )
    return f"""<svg viewBox="0 0 100 80" width="64" height="52">
        <line x1="8" y1="65" x2="92" y2="65" {_ICON_STROKE}/>
        {pile_svg}
        {walls_svg}
        <path d="M20 {base_y} A30 {dome_ry} 0 0 1 80 {base_y}" {_ICON_STROKE}{dash}/>
    </svg>"""


def _vertical_ellipsoid_icon():
    return f"""<svg viewBox="0 0 100 80" width="64" height="52">
        <ellipse cx="50" cy="49" rx="18" ry="28" {_ICON_STROKE}/>
        <line x1="8" y1="65" x2="92" y2="65" {_ICON_STROKE}/>
    </svg>"""


def _horizontal_ellipsoid_icon():
    return f"""<svg viewBox="0 0 100 80" width="64" height="52">
        <ellipse cx="50" cy="52" rx="38" ry="18" {_ICON_STROKE}/>
        <line x1="8" y1="65" x2="92" y2="65" {_ICON_STROKE}/>
    </svg>"""


def _ellipse_icon():
    return f"""<svg viewBox="0 0 100 80" width="64" height="52">
        <ellipse cx="50" cy="48" rx="38" ry="22" {_ICON_STROKE}/>
        <line x1="10" y1="48" x2="90" y2="48" stroke="#aaa" stroke-width="1.5" stroke-dasharray="3,3"/>
        <line x1="50" y1="24" x2="50" y2="72" stroke="#aaa" stroke-width="1.5" stroke-dasharray="3,3"/>
    </svg>"""


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
        "label": "Spherical Section",
        "diagram": diagrams.spherical(),
        "iso": iso.spherical(),
        "draw": drawings.spherical,
        "icon": _dome_icon(dome_ry=30),  # half sphere on the ground, no stem wall
        "icon_small": _dome_icon(dome_ry=30),
        "fields": [
            number_field("diameter", "Diameter", 105.0),
            number_field("height", "Height", 35.0),
            number_field("stem_wall", "Stem Wall", 0.0),
        ],
        "validate": _validate_spherical,
        "compute": lambda v: spherical_dome(v["diameter"], v["height"], v["stem_wall"]),
    },
    "ellipsoid": {
        "label": "Ellipsoid",
        "diagram": diagrams.ellipsoid(),
        "iso": iso.ellipsoid(),
        "draw": drawings.ellipsoid,
        "icon": _dome_icon(dome_ry=16.5),
        "fields": [
            number_field("diameter", "Diameter", 50.0),
            number_field("height", "Height", 20.0),
            number_field("stem_wall", "Stem Wall", 0.0),
        ],
        "validate": _validate_ellipsoid,
        "compute": lambda v: ellipsoid_dome(v["diameter"], v["height"], v["stem_wall"]),
    },
    "vertical_ellipsoid": {
        "label": "Vertical Ellipse",
        "diagram": diagrams.vertical_ellipsoid(),
        "iso": iso.vertical_ellipsoid(),
        "draw": drawings.vertical_ellipsoid,
        "icon": _vertical_ellipsoid_icon(),
        "fields": [
            number_field("horizontal", "Horizontal", 25.0),
            number_field("vertical", "Vertical", 16.5),
            number_field("height", "Height", 20.0),
        ],
        "validate": _validate_vertical_ellipsoid,
        "compute": lambda v: vertical_ellipsoid_dome(v["horizontal"], v["vertical"], v["height"]),
    },
    "horizontal_ellipsoid": {
        "label": "Horizontal Ellipse",
        "diagram": diagrams.horizontal_ellipsoid(),
        "iso": iso.horizontal_ellipsoid(),
        "draw": drawings.horizontal_ellipsoid,
        "icon": _horizontal_ellipsoid_icon(),
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
        "diagram": diagrams.ellipse2d(),
        "iso": iso.ellipse2d(),
        "draw": drawings.ellipse2d,
        "icon": _ellipse_icon(),
        "fields": [
            number_field("major", "Major Radius", 30.0),
            number_field("minor", "Minor Radius", 20.0),
        ],
        "validate": _validate_ellipse,
        "compute": lambda v: ellipse(v["major"], v["minor"]),
    },
    "dry_bulk_calculator": {
        "label": "Bulk Storage Calculator",
        "detail_prefixes": ["Cone @", "Portion above cone", "Frustum below cone", "Dome:", "Stem Wall:"],
        "diagram": diagrams.dry_bulk_calculator(),
        "iso": iso.dry_bulk_calculator(),
        "draw": drawings.dry_bulk_calculator,
        "icon": _dome_icon(dome_ry=30, stem_wall=True, pile=True),
        "icon_small": _dome_icon(dome_ry=30),
        "fields": [
            number_field("diameter", "Diameter", 116.0),
            number_field("height", "Height", 58.0),
            number_field("stem_wall", "Stem Wall", 36.0),
            plain_number_field("angle", "Angle of Repose", 32.0, "°"),
            plain_number_field("density", "Density", 50.0),
            select_field("density_unit", "Density Unit", "lbs/ft3", DENSITY_UNIT_CHOICES),
            number_field("freeboard", "Freeboard", FREEBOARD_DEFAULTS),
        ],
        "validate": _validate_dry_bulk_calculator,
        "compute": lambda v: dry_bulk_storage_dome(
            v["diameter"], v["height"], v["stem_wall"], v["angle"], v["density"], v["density_unit"], v["units"],
            v["freeboard"],
        ),
    },
    "dry_bulk_sizer": {
        "label": "Bulk Product Storage Sizer",
        "detail_prefixes": ["Cone @", "Portion above cone", "Frustum below cone", "Dome:", "Stem Wall:"],
        "diagram": diagrams.dry_bulk_sizer(),
        "iso": iso.dry_bulk_sizer(),
        "draw": drawings.dry_bulk_sizer,
        "icon": _dome_icon(dome_ry=30, stem_wall=True, pile=True, dashed=True),
        "icon_small": _dome_icon(dome_ry=30),
        "fields": [
            plain_number_field("angle", "Angle of Repose", 32.0, "°"),
            plain_number_field("density", "Density", 50.0),
            select_field("density_unit", "Density Unit", "lbs/ft3", DENSITY_UNIT_CHOICES),
            plain_number_field("capacity", "Capacity", 10000.0),
            select_field("weight_unit", "Capacity Unit", "ton", WEIGHT_UNIT_CHOICES),
            number_field("stem_wall", "Stem Wall", 16.0),
            number_field("freeboard", "Freeboard", FREEBOARD_DEFAULTS),
        ],
        "validate": _validate_dry_bulk_sizer,
        "compute": lambda v: dry_bulk_storage_sizer(
            v["capacity"], v["weight_unit"], v["density"], v["density_unit"], v["angle"], v["stem_wall"], v["units"],
            v["freeboard"],
        ),
    },
}

# The small breadcrumb card (steps 2-3) shows a simplified icon where one is
# set: the spherical-cap shapes reduce to a plain half-sphere section.
for _shape_config in SHAPES.values():
    _shape_config.setdefault("icon_small", _shape_config["icon"])


@app.route("/")
def index():
    shape_key = request.args.get("shape")
    if shape_key not in SHAPES:
        shape_key = None

    units = request.args.get("units")
    if units not in UNIT_CHOICES:
        units = None

    if shape_key is None:
        stage = 1
    elif units is None:
        stage = 2
    else:
        stage = 3

    if stage < 3:
        return render_template(
            "index.html",
            stage=stage,
            shape_key=shape_key,
            units=units,
            shapes=SHAPES,
            unit_choices=UNIT_CHOICES,
        )

    shape = SHAPES[shape_key]
    errors = []

    # Fresh arrival from step 2 has only shape+units in the URL; a Calculate
    # submission carries the field values. Don't show results (or the scaled
    # drawing) until the user has actually calculated at least once.
    submitted = any(request.args.get(field["key"]) is not None for field in shape["fields"])

    values = {}
    for field in shape["fields"]:
        key = field["key"]
        raw = request.args.get(key)
        if field["kind"] == "select":
            choices = [choice_value for choice_value, _choice_label in field["choices"]]
            values[key] = raw if raw in choices else field["default"]
        else:
            default = field["default"]
            if isinstance(default, dict):
                default = default[units]
            if raw is None:
                values[key] = default
            else:
                try:
                    values[key] = float(raw.replace(",", ""))
                except ValueError:
                    errors.append(f"'{raw}' is not a valid number for {field['label']}.")
                    values[key] = default

    values["units"] = units

    if submitted and not errors:
        errors = shape["validate"](values)

    results = None
    detail_results = None
    drawing = None
    if submitted and not errors:
        try:
            results = shape["compute"](values)
            drawing = shape["draw"](values)
        except ValueError as error:
            errors.append(str(error))
        else:
            detail_prefixes = shape.get("detail_prefixes", [])
            if detail_prefixes:
                detail_results = [
                    (title, rows) for title, rows in results
                    if any(title.startswith(prefix) for prefix in detail_prefixes)
                ]
                results = [
                    (title, rows) for title, rows in results
                    if not any(title.startswith(prefix) for prefix in detail_prefixes)
                ]

    return render_template(
        "index.html",
        stage=stage,
        shape_key=shape_key,
        units=units,
        shapes=SHAPES,
        unit_choices=UNIT_CHOICES,
        values=values,
        results=results,
        detail_results=detail_results,
        drawing=drawing,
        errors=errors,
    )


if __name__ == "__main__":
    import os

    # Default 5050: port 5000 is commonly occupied on macOS by the AirPlay
    # Receiver. A PORT env var (e.g. from a preview harness or PaaS) wins.
    app.run(debug=True, port=int(os.environ.get("PORT", "5050")))
