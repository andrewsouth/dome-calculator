"""To-scale drawings of the calculated structure, rendered after Calculate.

Each shape produces an architectural pair: a section/elevation view and,
directly below it at the same horizontal scale and centerline, a plan view
of the footprint -- so the plan's edges line up with the elevation above.
Drawn from the user's actual values with true proportions, plus a person
silhouette in the elevation for size reference.

Each draw function returns a list of (title, svg, caption) boxes.
"""

import math

from geometry import dry_bulk_geometry, live_dead_reclaim, solve_dry_bulk_dome_radius

STRUCT = 'stroke="#333" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"'
STRUCT_THIN = 'stroke="#333" stroke-width="1.8" fill="none"'
DASHED = 'stroke="#999" stroke-width="1.2" fill="none" stroke-dasharray="5,4"'
AXIS = 'stroke="#bbb" stroke-width="1" stroke-dasharray="4,4"'
PILE = 'fill="#e2e2e2" stroke="#999" stroke-width="1"'

PERSON_HEIGHT = {"ft": 6.0, "in": 72.0, "m": 1.83, "mm": 1830.0}
SCALE_CAPTION = "Drawn to scale &mdash; person shown for size reference"


def _mapper(xmin, xmax, ymin, ymax):
    """Fit a world-coordinate box (y up) into pixel space (y down)."""
    scale = min(300 / (xmax - xmin), 190 / (ymax - ymin))
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
    for the person to the right. Returns (scale, X, Y, svg_closer, width)."""
    person_h = PERSON_HEIGHT[units]
    person_x = half_width + 0.45 * person_h
    xmin, xmax = -half_width, half_width + 0.9 * person_h
    ymax = max(top_height, person_h)
    scale, width, height, x_px, y_px = _mapper(xmin, xmax, 0, ymax)

    ground = f'<line x1="{x_px(xmin)}" y1="{y_px(0)}" x2="{x_px(xmax)}" y2="{y_px(0)}" {STRUCT}/>'

    def close(body):
        return _svg(ground + body + _person(x_px, y_px, scale, person_x, units), width, height)

    return scale, x_px, y_px, close, width


def _plan_view(scale, x_px, width, solid, outer_dashed=None, inner_dashed=None):
    """Top view sharing the elevation's horizontal scale and centerline.

    `solid` is the footprint's (rx, ry) world semi-axes; `outer_dashed` marks
    a wider maximum extent above the floor (e.g. an ellipsoid's equator
    overhang) and `inner_dashed` a feature inside (e.g. the pile cone base).
    """
    extents = [solid] + [e for e in (outer_dashed, inner_dashed) if e]
    max_ry = max(ry for _rx, ry in extents)
    height = 2 * max_ry * scale + 40
    cx, cy = x_px(0), round(height / 2, 1)

    def ellipse(rx, ry, style):
        return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx * scale:.1f}" ry="{ry * scale:.1f}" {style}/>'

    body = ""
    if outer_dashed:
        body += ellipse(*outer_dashed, DASHED)
    body += ellipse(*solid, STRUCT_THIN)
    if inner_dashed:
        body += ellipse(*inner_dashed, DASHED)

    max_rx = max(rx for rx, _ry in extents)
    body += f'<line x1="{cx - max_rx * scale - 10:.1f}" y1="{cy}" x2="{cx + max_rx * scale + 10:.1f}" y2="{cy}" {AXIS}/>'
    body += f'<line x1="{cx}" y1="{cy - max_ry * scale - 10:.1f}" x2="{cx}" y2="{cy + max_ry * scale + 10:.1f}" {AXIS}/>'
    return _svg(body, width, height)


def _dome_profile_points(radius, dome_height, stem_wall, segments=48):
    """Sampled points along the true spherical-cap curve (world coords).

    Rendered as a polyline instead of an SVG arc: when a cap is at or near a
    hemisphere the chord equals the arc diameter, and the 0.1px rounding of
    arc parameters makes renderers visibly sag the curve. Sampling the true
    circle keeps the shell consistent with everything computed from it."""
    curvature = (radius ** 2 + dome_height ** 2) / (2 * dome_height)
    center_y = stem_wall + dome_height - curvature
    # Angle-uniform sampling: uniform-x chords sag visibly where the curve
    # turns vertical (a hemisphere's edges); uniform angle keeps chord error
    # below ~0.05 px at this size.
    t_start = math.acos(max(-1.0, -radius / curvature))
    t_end = math.acos(min(1.0, radius / curvature))
    pts = []
    for i in range(segments + 1):
        t = t_start + (t_end - t_start) * i / segments
        pts.append((curvature * math.cos(t), center_y + curvature * math.sin(t)))
    return pts


def _dome_body(radius, dome_height, stem_wall, scale, x_px, y_px):
    """Stem wall + spherical-cap profile."""
    profile = " ".join(
        f"{x_px(x)},{y_px(z)}" for x, z in _dome_profile_points(radius, dome_height, stem_wall)
    )
    return (
        f'<line x1="{x_px(-radius)}" y1="{y_px(0)}" x2="{x_px(-radius)}" y2="{y_px(stem_wall)}" {STRUCT}/>'
        f'<line x1="{x_px(radius)}" y1="{y_px(0)}" x2="{x_px(radius)}" y2="{y_px(stem_wall)}" {STRUCT}/>'
        f'<polyline points="{profile}" {STRUCT}/>'
    )


def _dome_pair(elevation_svg, plan_svg):
    return [
        ("Dome Section Elevation View", elevation_svg, SCALE_CAPTION),
        ("Dome Plan View", plan_svg, None),
    ]


def spherical(v):
    radius, height, wall = v["diameter"] / 2, v["height"], v["stem_wall"]
    scale, x_px, y_px, close, width = _ground_shape_frame(radius, wall + height, v["units"])
    elevation = close(_dome_body(radius, height, wall, scale, x_px, y_px))
    plan = _plan_view(scale, x_px, width, (radius, radius))
    return _dome_pair(elevation, plan)


def ellipsoid(v):
    radius, height, wall = v["diameter"] / 2, v["height"], v["stem_wall"]
    scale, x_px, y_px, close, width = _ground_shape_frame(radius, wall + height, v["units"])
    profile = " ".join(
        f"{x_px(radius * math.cos(math.pi * (1 - i / 48)))},"
        f"{y_px(wall + height * math.sin(math.pi * (1 - i / 48)))}"
        for i in range(49)
    )
    body = (
        f'<line x1="{x_px(-radius)}" y1="{y_px(0)}" x2="{x_px(-radius)}" y2="{y_px(wall)}" {STRUCT}/>'
        f'<line x1="{x_px(radius)}" y1="{y_px(0)}" x2="{x_px(radius)}" y2="{y_px(wall)}" {STRUCT}/>'
        f'<polyline points="{profile}" {STRUCT}/>'
    )
    plan = _plan_view(scale, x_px, width, (radius, radius))
    return _dome_pair(close(body), plan)


def _cut_ellipsoid_elevation(a, b, height, units):
    """Full ellipse (a horizontal, b vertical semi-axis) cut by the floor,
    with the below-floor remainder dashed. Returns the svg plus the frame
    pieces the aligned plan view needs."""
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
    return _svg(body, width, height_px), scale, x_px, width, floor_half


def vertical_ellipsoid(v):
    a, b, height = v["horizontal"], v["vertical"], v["height"]
    elevation, scale, x_px, width, floor_half = _cut_ellipsoid_elevation(a, b, height, v["units"])
    # Circular footprint; if the floor sits below the equator, the equator
    # overhangs it -- shown as a dashed outer circle.
    outer = (a, a) if a > floor_half * 1.001 else None
    plan = _plan_view(scale, x_px, width, (floor_half, floor_half), outer_dashed=outer)
    return _dome_pair(elevation, plan)


def horizontal_ellipsoid(v):
    a, b, height = v["major"], v["minor"], v["height"]
    elevation, scale, x_px, width, floor_half = _cut_ellipsoid_elevation(a, b, height, v["units"])
    # Elliptical footprint with the ellipsoid's own minor/major ratio; the
    # widest extent (if the floor is below the axis) is the full a x b shadow.
    floor_minor = floor_half * b / a
    outer = (a, b) if a > floor_half * 1.001 else None
    plan = _plan_view(scale, x_px, width, (floor_half, floor_minor), outer_dashed=outer)
    return _dome_pair(elevation, plan)


def ellipse2d(v):
    a, b = v["major"], v["minor"]
    scale, width, height, x_px, y_px = _mapper(-a, a, -b, b)
    body = (
        f'<ellipse cx="{x_px(0)}" cy="{y_px(0)}" rx="{a * scale:.1f}" ry="{b * scale:.1f}" {STRUCT}/>'
        f'<line x1="{x_px(-a)}" y1="{y_px(0)}" x2="{x_px(a)}" y2="{y_px(0)}" {AXIS}/>'
        f'<line x1="{x_px(0)}" y1="{y_px(-b)}" x2="{x_px(0)}" y2="{y_px(b)}" {AXIS}/>'
        f'<circle cx="{x_px(0)}" cy="{y_px(0)}" r="3" fill="#333"/>'
    )
    return [("Plan View", _svg(body, width, height), "Drawn to scale")]


def _pile_outline(core, stem_wall, dome_height):
    """World-coordinate outline of the stored pile: up the wall (and along
    the dome curve if the pile reaches past the stem wall) to the transition
    point, to the peak, mirrored down."""
    radius, curvature = core["radius"], core["radius_of_curvature"]
    transition, peak = core["transition_height"], core["pile_apex_height"]
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
    return left + [(0.0, peak)] + [(-x, y) for x, y in reversed(left)]


def _polygon_str(points, x_px, y_px):
    return " ".join(f"{x_px(x)},{y_px(y)}" for x, y in points)


def _dry_bulk_drawing(diameter, dome_height, stem_wall, angle, freeboard, units):
    core = dry_bulk_geometry(diameter, dome_height, stem_wall, angle, freeboard)
    radius = core["radius"]
    total = stem_wall + dome_height

    scale, x_px, y_px, close, width = _ground_shape_frame(radius, total, units)

    body = f'<polygon points="{_polygon_str(_pile_outline(core, stem_wall, dome_height), x_px, y_px)}" {PILE}/>'
    body += _dome_body(radius, dome_height, stem_wall, scale, x_px, y_px)
    elevation = close(body)

    # Plan: floor circle with the pile cone's base circle dashed inside.
    plan = _plan_view(
        scale, x_px, width, (radius, radius), inner_dashed=(core["cone_radius"], core["cone_radius"])
    )
    return _dome_pair(elevation, plan)


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


# -- Live & dead reclaim drawing --

HEAT_STOPS = [  # live column depth 0 -> max, light to dark
    (253, 246, 195), (159, 217, 179), (63, 143, 192), (18, 48, 107),
]


def _heat_color(fraction):
    fraction = min(max(fraction, 0.0), 1.0)
    scaled = fraction * (len(HEAT_STOPS) - 1)
    i = min(int(scaled), len(HEAT_STOPS) - 2)
    t = scaled - i
    rgb = [round(HEAT_STOPS[i][c] + (HEAT_STOPS[i + 1][c] - HEAT_STOPS[i][c]) * t) for c in range(3)]
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def live_dead(v):
    diameter, dome_height, stem_wall = v["diameter"], v["height"], v["stem_wall"]
    repose, drawdown, freeboard = v["angle"], v["drawdown"], v["freeboard"]
    open_w, open_l, units = v["opening_w"], v["opening_l"], v["units"]

    openings = [(0.0, 0.0, open_w, open_l)]
    reclaim = live_dead_reclaim(
        diameter, dome_height, stem_wall, repose, drawdown, freeboard, openings, samples=120
    )
    core = reclaim["core"]
    radius, total = core["radius"], stem_wall + dome_height
    apex, reach = core["pile_apex_height"], reclaim["channel_reach"]
    t_dd = math.tan(math.radians(drawdown))
    half_w = open_w / 2

    def surface(r):
        if r <= core["cone_radius"]:
            slope = (apex - core["transition_height"]) / core["cone_radius"] if core["cone_radius"] else 0
            return apex - slope * r
        center_y = stem_wall + dome_height - core["radius_of_curvature"]
        return min(total, center_y + math.sqrt(max(core["radius_of_curvature"] ** 2 - r ** 2, 0.0)))

    # Section: gray pile, blue live channel (funnel walls up from the opening
    # edges, capped by the product surface sampled to the channel reach).
    scale, x_px, y_px, close, width = _ground_shape_frame(radius, total, units)
    body = f'<polygon points="{_polygon_str(_pile_outline(core, stem_wall, dome_height), x_px, y_px)}" {PILE}/>'

    # Funnel walls rise from the opening edge; if the channel reaches the
    # stem wall before meeting the surface, live extends up the wall itself.
    funnel_at_reach = min(t_dd * max(reach - half_w, 0.0), surface(reach))
    live_pts = [(-half_w, 0.0), (-reach, funnel_at_reach), (-reach, surface(reach))]
    steps = 32
    for i in range(1, steps):
        x = -reach + (2 * reach) * i / steps
        live_pts.append((x, surface(abs(x))))
    live_pts += [(reach, surface(reach)), (reach, funnel_at_reach), (half_w, 0.0)]
    body += (
        f'<polygon points="{_polygon_str(live_pts, x_px, y_px)}" '
        'fill="#b5cbe8" stroke="#44608c" stroke-width="1.2" stroke-linejoin="round"/>'
    )
    body += f'<rect x="{x_px(-half_w)}" y="{y_px(0) - 3}" width="{(x_px(half_w) - x_px(-half_w)):.1f}" height="4" fill="#b03a2e"/>'
    body += _dome_body(radius, dome_height, stem_wall, scale, x_px, y_px)
    label = 'font-size="13" font-family="system-ui, sans-serif" font-weight="600"'
    body += f'<text x="{x_px(0)}" y="{y_px(apex * 0.35)}" text-anchor="middle" fill="#2c4a7c" {label}>LIVE</text>'
    body += f'<text x="{x_px(-radius * 0.72)}" y="{y_px(stem_wall * 0.3)}" text-anchor="middle" fill="#777" {label}>DEAD</text>'
    body += f'<text x="{x_px(radius * 0.72)}" y="{y_px(stem_wall * 0.3)}" text-anchor="middle" fill="#777" {label}>DEAD</text>'
    elevation = close(body)

    # Plan heatmap: concentric bands of DEAD pile depth (near-radial for a
    # centered opening). Dead depth is the material below the funnel line --
    # min(channel height, product surface): zero over the opening, deepest
    # at the channel-reach ring, tapering as the surface drops to the wall.
    height_px = 2 * radius * scale + 40
    cx, cy = x_px(0.0), round(height_px / 2, 1)

    def dead_depth(r):
        return min(t_dd * max(r - half_w, 0.0), surface(r))

    bands = 20
    max_depth = max(dead_depth(radius * i / 200) for i in range(201)) or 1.0
    heat = ""
    for i in range(bands, 0, -1):
        r = radius * i / bands
        r_mid = radius * (i - 0.5) / bands
        heat += (
            f'<circle cx="{cx}" cy="{cy}" r="{r * scale:.1f}" '
            f'fill="{_heat_color(dead_depth(r_mid) / max_depth)}" stroke="none"/>'
        )
    heat += (
        f'<rect x="{cx - half_w * scale:.1f}" y="{cy - open_l / 2 * scale:.1f}" '
        f'width="{open_w * scale:.1f}" height="{open_l * scale:.1f}" '
        'fill="#b03a2e" stroke="#fff" stroke-width="1"/>'
    )
    heat += f'<circle cx="{cx}" cy="{cy}" r="{radius * scale:.1f}" {STRUCT_THIN}/>'
    plan = _svg(heat, width, height_px)

    axo = _dead_pile_axo(core, reclaim, stem_wall, dome_height, open_w, open_l, funnel_at_reach)
    return [
        ("Reclaim Section — Live & Dead", elevation, SCALE_CAPTION),
        ("Plan — Dead Pile Depth", plan, "Darker is deeper dead material; red is the hopper opening"),
        ("Axonometric — Dead Pile (Cutaway)", axo, "Front half removed at the section plane; gray material is dead"),
    ]


def _dead_pile_axo(core, reclaim, stem_wall, dome_height, open_w, open_l, rim_z):
    """Cutaway 3D-look view of what remains after gravity discharge: the
    front half is sliced away at the section plane, exposing the dead
    material as two cross-section wedges with the drawdown funnel emptied
    all the way down to the opening between them. Proportions come from the
    calculated geometry (crater rim at the channel reach radius, at the
    funnel's height there)."""
    K = 0.35  # foreshortening for plan circles
    R, total = core["radius"], stem_wall + dome_height
    transition = core["transition_height"]
    reach = reclaim["channel_reach"]
    half_w = open_w / 2

    s = min(95.0 / R, 140.0 / total)
    cx, ground = 150.0, 168.0

    def X(x):
        return round(cx + x * s, 1)

    def Y(z):
        return round(ground - z * s, 1)

    r_vis = R * s
    base_ry = r_vis * K
    rim_rx, rim_ry = max(reach * s, 4.0), max(reach * s * K, 1.5)
    # Dead height at the wall: the product contact height normally, but only
    # the funnel height when the channel reaches the wall itself.
    wall_top = min(transition, stem_wall)
    if reach >= R * 0.999:
        wall_top = min(wall_top, rim_z)

    body = ""
    # Back half of the floor ring.
    body += (
        f'<path d="M{X(-R)} {Y(0)} A{r_vis:.1f} {base_ry:.1f} 0 0 1 {X(R)} {Y(0)}" '
        'stroke="#aaa" stroke-width="1.2" fill="none"/>'
    )
    # Far wall of the funnel: back arc of the crater rim descending to the
    # opening -- the surface the material slides down during discharge.
    body += (
        f'<path d="M{X(-reach)} {Y(rim_z)} A{rim_rx:.1f} {rim_ry:.1f} 0 0 1 {X(reach)} {Y(rim_z)} '
        f'L{X(half_w)} {Y(0)} L{X(-half_w)} {Y(0)} Z" '
        'fill="#cfcfcf" stroke="#8a8a8a" stroke-width="1" stroke-linejoin="round"/>'
    )
    # Cut-face wedges: the dead cross-section at the slice plane.
    wedge = 'fill="#e0e0e0" stroke="#777" stroke-width="1.5" stroke-linejoin="round"'
    body += (
        f'<path d="M{X(-R)} {Y(0)} L{X(-R)} {Y(wall_top)} L{X(-reach)} {Y(rim_z)} '
        f'L{X(-half_w)} {Y(0)} Z" {wedge}/>'
    )
    body += (
        f'<path d="M{X(R)} {Y(0)} L{X(R)} {Y(wall_top)} L{X(reach)} {Y(rim_z)} '
        f'L{X(half_w)} {Y(0)} Z" {wedge}/>'
    )
    # Slice line along the floor and the opening at the funnel's foot.
    body += f'<line x1="{X(-R)}" y1="{Y(0)}" x2="{X(R)}" y2="{Y(0)}" stroke="#666" stroke-width="1"/>'
    body += (
        f'<rect x="{X(-half_w)}" y="{Y(0) - max(open_l * s * K, 2.0) / 2:.1f}" '
        f'width="{max(open_w * s, 3.0):.1f}" height="{max(open_l * s * K, 2.0):.1f}" fill="#b03a2e"/>'
    )
    # Ghost of the dome shell for context.
    shell = " ".join(
        f"{X(x)},{Y(z)}" for x, z in _dome_profile_points(R, dome_height, stem_wall, segments=36)
    )
    body += f'<polyline points="{shell}" {DASHED}/>'
    body += (
        f'<line x1="{X(-R)}" y1="{Y(0)}" x2="{X(-R)}" y2="{Y(stem_wall)}" {DASHED}/>'
        f'<line x1="{X(R)}" y1="{Y(0)}" x2="{X(R)}" y2="{Y(stem_wall)}" {DASHED}/>'
    )
    label = 'font-size="12" font-family="system-ui, sans-serif" font-weight="600" fill="#777"'
    mid_x = (R + max(reach, half_w)) / 2
    body += f'<text x="{X(-mid_x * 0.92)}" y="{Y(wall_top * 0.22)}" text-anchor="middle" {label}>DEAD</text>'
    body += f'<text x="{X(mid_x * 0.92)}" y="{Y(wall_top * 0.22)}" text-anchor="middle" {label}>DEAD</text>'

    height_px = ground + base_ry + 14
    return _svg(body, 300, height_px)
