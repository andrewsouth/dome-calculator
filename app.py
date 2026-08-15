import math

from flask import Flask, render_template, request

import diagrams
import drawings
import iso
from geometry import (
    BU_TO_FT3,
    FT3_TO_M3,
    LB_TO_KG,
    US_TON_TO_KG,
    dry_bulk_storage_dome,
    live_dead_storage,
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
WEIGHT_UNIT_CHOICES = [("ton", "ton"), ("lbs", "lbs"), ("tonne", "tonne"), ("kg", "kg")]
# Density-unit conversion factors to kg/m3, for converting the density value
# in place when its unit selector changes (75 lbs/ft3 should become 1.20 t/m3,
# not be reinterpreted as 75 t/m3).
DENSITY_TO_KG_M3 = {"lbs/ft3": 16.018463, "kg/m3": 1.0, "t/m3": 1000.0}
# Weight-unit conversion for the capacity value. Mass units convert to kg
# directly; bushels are a volume measure, so bu conversions route through the
# form's current density.
WEIGHT_TO_KG = {"lbs": LB_TO_KG, "ton": US_TON_TO_KG, "kg": 1.0, "tonne": 1000.0}
BU_M3 = BU_TO_FT3 * FT3_TO_M3
# Length-unit conversion factors to meters, for converting entered values in
# place when the user switches units on the dimensions step.
UNIT_TO_M = {"ft": 0.3048, "in": 0.0254, "m": 1.0, "mm": 0.001}
# Freeboard default depends on the selected length unit: 1.5 ft or 0.5 m.
FREEBOARD_DEFAULTS = {"ft": 1.5, "in": 18.0, "m": 0.5, "mm": 500.0}
# Default center-to-center spacing for multi-hopper layouts: 15 ft or 5 m.
SPACING_DEFAULTS = {"ft": 15.0, "in": 180.0, "m": 5.0, "mm": 5000.0}


def number_field(key, label, default):
    return {"key": key, "label": label, "default": default, "kind": "number", "unit": "length"}


def count_field(key, label, default):
    """A whole-number field (hopper/tunnel counts): rendered without
    decimals and validated as an integer."""
    return {"key": key, "label": label, "default": default, "kind": "number",
            "unit": "", "integer": True}


def plain_number_field(key, label, default, suffix=""):
    return {"key": key, "label": label, "default": default, "kind": "number", "unit": suffix}


def volume_field(key, label, default):
    return {"key": key, "label": label, "default": default, "kind": "number", "unit": "volume"}


def select_field(key, label, default, choices, convert=False):
    """A dropdown field; convert=True marks unit selectors whose change
    should convert the paired value in place (handled in the route)."""
    return {"key": key, "label": label, "default": default, "kind": "select",
            "choices": choices, "convert": convert}


_ICON_STROKE = 'stroke="#444" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"'


def _dome_icon(dome_ry=30, stem_wall=False, pile=False, dashed=False, funnel=False):
    """Ground line + dome arc (radius 30, chord 20..80); optional stem wall,
    dashed outline, a product pile at a ~30 degree angle of repose, and a
    reclaim funnel channel inside the pile."""
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
    funnel_svg = (
        '<polygon points="46,64 54,64 73,33 50,20 27,33" '
        'fill="#a9c4e4" stroke="#44608c" stroke-width="1.5" stroke-linejoin="round"/>'
        if funnel else ""
    )
    return f"""<svg viewBox="0 0 100 80" width="64" height="52">
        <line x1="8" y1="65" x2="92" y2="65" {_ICON_STROKE}/>
        {pile_svg}
        {funnel_svg}
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


def _validate_live_dead(v):
    errors = _validate_dry_bulk_calculator(v)
    if not (v["angle"] < v["drawdown"] < 90):
        errors.append("Drawdown angle must be steeper than the angle of repose and less than 90 degrees.")
    if v["opening_w"] <= 0 or v["opening_l"] <= 0:
        errors.append("Opening dimensions must be greater than 0.")
    elif v["opening_w"] >= v["diameter"] or v["opening_l"] >= v["diameter"]:
        errors.append("Opening must be smaller than the dome diameter.")
    if not (0 <= v["required_live"] < 100):
        errors.append("Target live must be a percentage from 0 to less than 100.")

    hoppers, tunnels = v["hoppers"], v["tunnels"]
    if hoppers != int(hoppers) or hoppers < 1:
        errors.append("Hoppers per tunnel must be a whole number of 1 or more.")
    if tunnels != int(tunnels) or tunnels < 1:
        errors.append("Tunnels must be a whole number of 1 or more.")
    if errors:
        return errors

    hoppers, tunnels = int(hoppers), int(tunnels)
    if hoppers * tunnels > 40:
        errors.append("Layout is limited to 40 openings total (hoppers per tunnel × tunnels).")
    if hoppers > 1 and v["hopper_spacing"] < v["opening_w"]:
        errors.append("Hopper spacing (center-to-center) must be at least the opening width, or openings overlap.")
    if tunnels > 1 and v["tunnel_spacing"] < v["opening_l"]:
        errors.append("Tunnel spacing (center-to-center) must be at least the opening length, or openings overlap.")
    if not errors:
        # The outermost opening corner must stay inside the dome footprint.
        corner_x = (hoppers - 1) / 2 * v["hopper_spacing"] + v["opening_w"] / 2
        corner_y = (tunnels - 1) / 2 * v["tunnel_spacing"] + v["opening_l"] / 2
        if math.hypot(corner_x, corner_y) >= v["diameter"] / 2:
            errors.append("Hopper layout extends beyond the dome footprint — reduce counts or spacing.")
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
        "category": "geometry",
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
        "category": "geometry",
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
        "category": "geometry",
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
        "category": "geometry",
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
        "category": "geometry",
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
        "category": "storage",
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
            select_field("density_unit", "Density Unit", "lbs/ft3", DENSITY_UNIT_CHOICES, convert=True),
            number_field("freeboard", "Freeboard", FREEBOARD_DEFAULTS),
        ],
        "validate": _validate_dry_bulk_calculator,
        "compute": lambda v: dry_bulk_storage_dome(
            v["diameter"], v["height"], v["stem_wall"], v["angle"], v["density"], v["density_unit"], v["units"],
            v["freeboard"],
        ),
    },
    "dry_bulk_sizer": {
        "label": "Product Storage Sizer",
        "category": "storage",
        "detail_prefixes": ["Cone @", "Portion above cone", "Frustum below cone", "Dome:", "Stem Wall:"],
        "diagram": diagrams.dry_bulk_sizer(),
        "iso": iso.dry_bulk_sizer(),
        "draw": drawings.dry_bulk_sizer,
        "icon": _dome_icon(dome_ry=30, stem_wall=True, pile=True, dashed=True),
        "icon_small": _dome_icon(dome_ry=30),
        "fields": [
            plain_number_field("angle", "Angle of Repose", 32.0, "°"),
            plain_number_field("density", "Density", 50.0),
            select_field("density_unit", "Density Unit", "lbs/ft3", DENSITY_UNIT_CHOICES, convert=True),
            plain_number_field("capacity", "Capacity", 10000.0),
            select_field("weight_unit", "Capacity Unit", "ton", WEIGHT_UNIT_CHOICES, convert=True),
            number_field("stem_wall", "Stem Wall", 16.0),
            number_field("freeboard", "Freeboard", FREEBOARD_DEFAULTS),
        ],
        "validate": _validate_dry_bulk_sizer,
        "compute": lambda v: dry_bulk_storage_sizer(
            v["capacity"], v["weight_unit"], v["density"], v["density_unit"], v["angle"], v["stem_wall"], v["units"],
            v["freeboard"],
        ),
    },
    "live_dead": {
        "label": "Live vs. Dead Storage",
        "category": "storage",
        "detail_prefixes": [
            "Cone @", "Portion above cone", "Frustum below cone",
            "Floor:", "Dome:", "Stem Wall:", "Total:",
        ],
        "diagram": diagrams.live_dead(),
        "iso": iso.dry_bulk_calculator(),
        "draw": drawings.live_dead,
        "icon": _dome_icon(dome_ry=30, stem_wall=True, pile=True, funnel=True),
        "icon_small": _dome_icon(dome_ry=30),
        "fields": [
            number_field("diameter", "Diameter", 60.0),
            number_field("height", "Height", 30.0),
            number_field("stem_wall", "Stem Wall", 30.0),
            plain_number_field("angle", "Angle of Repose", 25.0, "°"),
            plain_number_field("drawdown", "Drawdown Angle", 30.0, "°"),
            plain_number_field("density", "Density", 75.0),
            select_field("density_unit", "Density Unit", "lbs/ft3", DENSITY_UNIT_CHOICES, convert=True),
            number_field("freeboard", "Freeboard", FREEBOARD_DEFAULTS),
            number_field("opening_w", "Opening Width", 5.0),
            number_field("opening_l", "Opening Length", 5.0),
            count_field("hoppers", "Hoppers per Tunnel", 1.0),
            number_field("hopper_spacing", "Hopper Spacing", SPACING_DEFAULTS),
            count_field("tunnels", "Tunnels", 1.0),
            number_field("tunnel_spacing", "Tunnel Spacing", SPACING_DEFAULTS),
            plain_number_field("required_live", "Target Live", 0.0, "%"),
        ],
        "validate": _validate_live_dead,
        "compute": lambda v: live_dead_storage(
            v["diameter"], v["height"], v["stem_wall"], v["angle"], v["drawdown"],
            v["density"], v["density_unit"], v["units"], v["freeboard"],
            v["opening_w"], v["opening_l"], v["required_live"],
            v["hoppers"], v["hopper_spacing"], v["tunnels"], v["tunnel_spacing"],
        ),
    },
}

CATEGORIES = [
    ("geometry", "Shape & Geometry", "Dimensions, areas, and volumes of dome shapes and ellipses."),
    ("storage", "Bulk Product Storage", "Capacity of product piled inside a storage dome, or the dome size needed for a target capacity."),
]

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
            categories=CATEGORIES,
            unit_choices=UNIT_CHOICES,
        )

    shape = SHAPES[shape_key]
    errors = []

    # Results (and the scaled drawings) appear only after Calculate has been
    # pressed at least once -- the button submits go=1, which then persists
    # through in-place unit switches via a hidden field.
    submitted = request.args.get("go") == "1"

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

    # In-place density-unit switch: convert the density value so the same
    # physical material is preserved under the new unit.
    prev_density_unit = request.args.get("prev_density_unit")
    if (
        "density" in values and "density_unit" in values
        and prev_density_unit in DENSITY_TO_KG_M3
        and prev_density_unit != values["density_unit"]
    ):
        values["density"] *= (
            DENSITY_TO_KG_M3[prev_density_unit] / DENSITY_TO_KG_M3[values["density_unit"]]
        )

    # In-place capacity-unit switch: convert the capacity value so the same
    # physical amount of product is preserved under the new unit.
    prev_weight_unit = request.args.get("prev_weight_unit")
    if (
        "capacity" in values and "weight_unit" in values
        and prev_weight_unit in (list(WEIGHT_TO_KG) + ["bu"])
        and prev_weight_unit != values["weight_unit"]
        and values.get("density", 0) > 0
    ):
        density_kg_m3 = values["density"] * DENSITY_TO_KG_M3[values["density_unit"]]
        if prev_weight_unit == "bu":
            mass_kg = values["capacity"] * BU_M3 * density_kg_m3
        else:
            mass_kg = values["capacity"] * WEIGHT_TO_KG[prev_weight_unit]
        if values["weight_unit"] == "bu":
            values["capacity"] = mass_kg / density_kg_m3 / BU_M3
        else:
            values["capacity"] = mass_kg / WEIGHT_TO_KG[values["weight_unit"]]

    # In-place unit switch: convert already-entered lengths and volumes so
    # the same physical structure is preserved under the new unit.
    prev_units = request.args.get("prev_units")
    if prev_units in UNIT_CHOICES and prev_units != units:
        factor = UNIT_TO_M[prev_units] / UNIT_TO_M[units]
        for field in shape["fields"]:
            if field.get("unit") == "length":
                values[field["key"]] *= factor
            elif field.get("unit") == "volume":
                values[field["key"]] *= factor ** 3

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
        submitted=submitted,
    )


if __name__ == "__main__":
    import os

    # Default 5050: port 5000 is commonly occupied on macOS by the AirPlay
    # Receiver. A PORT env var (e.g. from a preview harness or PaaS) wins.
    app.run(debug=True, port=int(os.environ.get("PORT", "5050")))
