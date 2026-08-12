"""To-scale drawings of the calculated structure, rendered after Calculate.

Unlike the schematic input diagrams (diagrams.py), these are drawn from the
user's actual values with true proportions -- correct dome curvature, real
stem-wall-to-dome ratio, the actual material pile for the storage
calculators -- plus a person silhouette for size reference.
"""

import math

from geometry import dry_bulk_geometry, solve_dry_bulk_dome_radius

STRUCT = 'stroke="#333" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"'
DASHED = 'stroke="#999" stroke-width="1.5" fill="none" stroke-dasharray="6,5"'
PILE = 'fill="#e2e2e2" stroke="#999" stroke-width="1"'

PERSON_HEIGHT = {"ft": 6.0, "in": 72.0, "m": 1.83, "mm": 1830.0}


def _mapper(xmin, xmax, ymin, ymax):
    """Fit a world-coordinate box (y up) into pixel space (y down)."""
    scale = min(600 / (xmax - xmin), 380 / (ymax - ymin))
    width = (xmax - xmin) * scale + 40
    height = (ymax - ymin) * scale + 40

    def x_px(x):
        return round(20 + (x - xmin) * scale, 1)

    def y_px(y):
        return round(height - 20 - (y - ymin) * scale, 1)

    return scale, width, height, x_px, y_px


def _svg(body, width, height):
    return (
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" '
        f'style="max-width:100%;height:auto">{body}</svg>'
    )


def _person(x_px, y_px, scale, x_world, units):
    """Simple silhouette standing on the ground, drawn at true relative height."""
    h = PERSON_HEIGHT[units] * scale
    x, y0 = x_px(x_world), y_px(0)
    r = h * 0.13
    sw = max(1.2, h * 0.05)
    stroke = f'stroke="#777" stroke-width="{sw:.1f}" stroke-linecap="round" fill="none"'
    return (
        f'<circle cx="{x}" cy="{y0 - h + r:.1f}" r="{r:.1f}" fill="#777"/>'
        f'<line x1="{x}" y1="{y0 - h + 2 * r:.1f}" x2="{x}" y2="{y0 - h * 0.42:.1f}" {stroke}/>'
        f'<line x1="{x - h * 0.16:.1f}" y1="{y0 - h * 0.62:.1f}" x2="{x + h * 0.16:.1f}" y2="{y0 - h * 0.62:.1f}" {stroke}/>'
        f'<line x1="{x}" y1="{y0 - h * 0.42:.1f}" x2="{x - h * 0.12:.1f}" y2="{y0}" {stroke}/>'
        f'<line x1="{x}" y1="{y0 - h * 0.42:.1f}" x2="{x + h * 0.12:.1f}" y2="{y0}" {stroke}/>'
    )


def _ground_shape_frame(half_width, top_height, units):
    """Common mapper setup for shapes that sit on a ground line, leaving room
    for the person to the right. Returns (scale, X, Y, person_x, svg_closer)."""
    person_h = PERSON_HEIGHT[units]
    person_x = half_width + 0.45 * person_h
    xmin, xmax = -half_width, half_width + 0.9 * person_h
    ymax = max(top_height, person_h)
    scale, width, height, x_px, y_px = _mapper(xmin, xmax, 0, ymax)

    ground = f'<line x1="{x_px(xmin)}" y1="{y_px(0)}" x2="{x_px(xmax)}" y2="{y_px(0)}" {STRUCT}/>'

    def close(body):
        return _svg(ground + body + _person(x_px, y_px, scale, person_x, units), width, height)

    return scale, x_px, y_px, close


def _dome_body(radius, dome_height, stem_wall, scale, x_px, y_px):
    """Stem wall + spherical-cap arc with the true radius of curvature."""
    curvature = (radius ** 2 + dome_height ** 2) / (2 * dome_height)
    large = 1 if dome_height > radius else 0
    body = (
        f'<line x1="{x_px(-radius)}" y1="{y_px(0)}" x2="{x_px(-radius)}" y2="{y_px(stem_wall)}" {STRUCT}/>'
        f'<line x1="{x_px(radius)}" y1="{y_px(0)}" x2="{x_px(radius)}" y2="{y_px(stem_wall)}" {STRUCT}/>'
        f'<path d="M{x_px(-radius)} {y_px(stem_wall)} '
        f'A {curvature * scale:.1f} {curvature * scale:.1f} 0 {large} 1 '
        f'{x_px(radius)} {y_px(stem_wall)}" {STRUCT}/>'
    )
    return body


def spherical(v):
    radius, height, wall = v["diameter"] / 2, v["height"], v["stem_wall"]
    scale, x_px, y_px, close = _ground_shape_frame(radius, wall + height, v["units"])
    return close(_dome_body(radius, height, wall, scale, x_px, y_px))


def ellipsoid(v):
    radius, height, wall = v["diameter"] / 2, v["height"], v["stem_wall"]
    scale, x_px, y_px, close = _ground_shape_frame(radius, wall + height, v["units"])
    body = (
        f'<line x1="{x_px(-radius)}" y1="{y_px(0)}" x2="{x_px(-radius)}" y2="{y_px(wall)}" {STRUCT}/>'
        f'<line x1="{x_px(radius)}" y1="{y_px(0)}" x2="{x_px(radius)}" y2="{y_px(wall)}" {STRUCT}/>'
        f'<path d="M{x_px(-radius)} {y_px(wall)} '
        f'A {radius * scale:.1f} {height * scale:.1f} 0 0 1 {x_px(radius)} {y_px(wall)}" {STRUCT}/>'
    )
    return close(body)


def _cut_ellipsoid(a, b, height, units):
    """Full ellipse (a horizontal, b vertical semi-axis) cut by the floor,
    with the below-floor remainder dashed. Shared by vertical & horizontal."""
    z_floor = b - height
    center_y = -z_floor  # world y of the ellipse center (floor is y=0)
    floor_half = a * math.sqrt(max(0.0, 1 - (z_floor / b) ** 2))
    large = 1 if height > b else 0

    person_h = PERSON_HEIGHT[units]
    person_x = a + 0.45 * person_h
    xmin, xmax = -a, a + 0.9 * person_h
    ymin = min(0.0, center_y - b)
    ymax = max(height, person_h)
    scale, width, height_px, x_px, y_px = _mapper(xmin, xmax, ymin, ymax)

    body = (
        f'<ellipse cx="{x_px(0)}" cy="{y_px(center_y)}" rx="{a * scale:.1f}" ry="{b * scale:.1f}" {DASHED}/>'
        f'<line x1="{x_px(xmin)}" y1="{y_px(0)}" x2="{x_px(xmax)}" y2="{y_px(0)}" {STRUCT}/>'
        f'<path d="M{x_px(-floor_half)} {y_px(0)} '
        f'A {a * scale:.1f} {b * scale:.1f} 0 {large} 1 {x_px(floor_half)} {y_px(0)}" {STRUCT}/>'
    )
    body += _person(x_px, y_px, scale, person_x, units)
    return _svg(body, width, height_px)


def vertical_ellipsoid(v):
    return _cut_ellipsoid(v["horizontal"], v["vertical"], v["height"], v["units"])


def horizontal_ellipsoid(v):
    return _cut_ellipsoid(v["major"], v["minor"], v["height"], v["units"])


def ellipse2d(v):
    a, b = v["major"], v["minor"]
    scale, width, height, x_px, y_px = _mapper(-a, a, -b, b)
    body = (
        f'<ellipse cx="{x_px(0)}" cy="{y_px(0)}" rx="{a * scale:.1f}" ry="{b * scale:.1f}" {STRUCT}/>'
        f'<line x1="{x_px(-a)}" y1="{y_px(0)}" x2="{x_px(a)}" y2="{y_px(0)}" '
        'stroke="#bbb" stroke-width="1" stroke-dasharray="4,4"/>'
        f'<line x1="{x_px(0)}" y1="{y_px(-b)}" x2="{x_px(0)}" y2="{y_px(b)}" '
        'stroke="#bbb" stroke-width="1" stroke-dasharray="4,4"/>'
        f'<circle cx="{x_px(0)}" cy="{y_px(0)}" r="3" fill="#333"/>'
    )
    return _svg(body, width, height)


def _dry_bulk_drawing(diameter, dome_height, stem_wall, angle, freeboard, units):
    core = dry_bulk_geometry(diameter, dome_height, stem_wall, angle, freeboard)
    radius, curvature = core["radius"], core["radius_of_curvature"]
    transition, peak = core["transition_height"], core["pile_apex_height"]
    total = stem_wall + dome_height

    scale, x_px, y_px, close = _ground_shape_frame(radius, total, units)

    # Pile outline: up the wall (and along the dome curve if the pile reaches
    # past the stem wall) to the transition point, to the peak, mirrored down.
    center_y = stem_wall + dome_height - curvature  # dome sphere center, world y
    left = [(-radius, 0.0)]
    if transition <= stem_wall:
        left.append((-radius, transition))
    else:
        left.append((-radius, stem_wall))
        steps = 14
        for i in range(1, steps + 1):
            y = stem_wall + (transition - stem_wall) * i / steps
            x = math.sqrt(max(curvature ** 2 - (y - center_y) ** 2, 0.0))
            left.append((-x, y))
    points = left + [(0.0, peak)] + [(-x, y) for x, y in reversed(left)]
    point_str = " ".join(f"{x_px(x)},{y_px(y)}" for x, y in points)

    body = f'<polygon points="{point_str}" {PILE}/>'
    body += _dome_body(radius, dome_height, stem_wall, scale, x_px, y_px)
    return close(body)


def dry_bulk_calculator(v):
    return _dry_bulk_drawing(
        v["diameter"], v["height"], v["stem_wall"], v["angle"], v["freeboard"], v["units"]
    )


def dry_bulk_sizer(v):
    radius = solve_dry_bulk_dome_radius(
        v["capacity"], v["weight_unit"], v["density"], v["density_unit"],
        v["angle"], v["stem_wall"], v["units"], v["freeboard"],
    )
    return _dry_bulk_drawing(2 * radius, radius, v["stem_wall"], v["angle"], v["freeboard"], v["units"])
