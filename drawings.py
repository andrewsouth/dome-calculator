"""To-scale drawings of the calculated structure, rendered after Calculate.

Each shape produces an architectural pair: a section/elevation view and,
directly below it at the same horizontal scale and centerline, a plan view
of the footprint -- so the plan's edges line up with the elevation above.
Drawn from the user's actual values with true proportions, plus a person
silhouette in the elevation for size reference.

Each draw function returns a list of (title, svg, caption) boxes.
"""

import math
import re

from geometry import (
    dry_bulk_geometry,
    hopper_layout,
    live_dead_reclaim,
    solve_dry_bulk_dome_radius,
)

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


def _hstack(panels, gap=16, label_h=18):
    """Place complete SVGs side by side inside one outer SVG, each with a
    small label centered above it. SVG nests cleanly: the inner documents
    keep their own coordinate systems, and the outer viewBox scales the
    whole row down together if the page is narrower."""
    parsed = []
    for panel_label, svg in panels:
        w, h = (int(n) for n in re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).groups())
        parsed.append((panel_label, svg, w, h))
    total_w = sum(w for _l, _s, w, _h in parsed) + gap * (len(parsed) - 1)
    total_h = label_h + max(h for _l, _s, _w, h in parsed)

    x = 0
    body = ""
    for panel_label, svg, w, h in parsed:
        body += (
            f'<text x="{x + w / 2:.0f}" y="12" text-anchor="middle" font-size="12" '
            f'font-family="system-ui, sans-serif" font-weight="600" fill="#666">{panel_label}</text>'
        )
        inner = svg.replace(' style="max-width:100%;height:auto"', "", 1)
        body += inner.replace("<svg ", f'<svg x="{x}" y="{label_h}" height="{h}" ', 1)
        x += w + gap
    return _svg(body, total_w, total_h)


# -- Live & dead reclaim drawing --

HEAT_STOPS = [  # live column depth 0 -> max, light to dark
    (253, 246, 195), (159, 217, 179), (63, 143, 192), (18, 48, 107),
]


def _heat_color(fraction, shade=1.0):
    """Palette color for a 0..1 dead depth; `shade` < 1 darkens (used by the
    isometric view to keep steep crater walls readable)."""
    fraction = min(max(fraction, 0.0), 1.0)
    scaled = fraction * (len(HEAT_STOPS) - 1)
    i = min(int(scaled), len(HEAT_STOPS) - 2)
    t = scaled - i
    rgb = [
        round((HEAT_STOPS[i][c] + (HEAT_STOPS[i + 1][c] - HEAT_STOPS[i][c]) * t) * shade)
        for c in range(3)
    ]
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def live_dead(v):
    diameter, dome_height, stem_wall = v["diameter"], v["height"], v["stem_wall"]
    repose, drawdown, freeboard = v["angle"], v["drawdown"], v["freeboard"]
    open_w, open_l, units = v["opening_w"], v["opening_l"], v["units"]
    hoppers, tunnels = int(v.get("hoppers", 1)), int(v.get("tunnels", 1))
    hopper_spacing = v.get("hopper_spacing", 0.0)
    tunnel_spacing = v.get("tunnel_spacing", 0.0)

    openings = hopper_layout(open_w, open_l, hoppers, hopper_spacing, tunnels, tunnel_spacing)
    reclaim = live_dead_reclaim(
        diameter, dome_height, stem_wall, repose, drawdown, freeboard, openings, samples=120
    )
    core = reclaim["core"]
    radius, total = core["radius"], stem_wall + dome_height
    apex = core["pile_apex_height"]
    t_dd = math.tan(math.radians(drawdown))

    def surface(r):
        if r <= core["cone_radius"]:
            slope = (apex - core["transition_height"]) / core["cone_radius"] if core["cone_radius"] else 0
            return apex - slope * r
        center_y = stem_wall + dome_height - core["radius_of_curvature"]
        return min(total, center_y + math.sqrt(max(core["radius_of_curvature"] ** 2 - r ** 2, 0.0)))

    def channel_at(x, y):
        return t_dd * min(
            math.hypot(max(abs(x - cx) - w / 2, 0.0), max(abs(y - cy) - l / 2, 0.0))
            for cx, cy, w, l in openings
        )

    def section_panel(cut, along_x):
        """One to-scale section through the pile. along_x=True cuts along a
        tunnel line (the center tunnel, or the first tunnel off-center when
        the count is even), so every hopper in that tunnel shows its funnel;
        along_x=False is the 90-degree cut across the tunnels through a
        hopper row, showing one funnel per tunnel. Adjacent funnels merge
        where the channel stays below the product surface between openings."""
        scale, x_px, y_px, close, _width = _ground_shape_frame(radius, total, units)
        body = f'<polygon points="{_polygon_str(_pile_outline(core, stem_wall, dome_height), x_px, y_px)}" {PILE}/>'

        def channel(s):
            return channel_at(s, cut) if along_x else channel_at(cut, s)

        # Sample the channel surface along the cut and collect the contiguous
        # runs where product stands above it: each run is one live region,
        # bounded above by the product surface and below by the channel
        # (clipped to the surface, so wall run-ups close cleanly).
        n_sec = 360
        tiny = total * 1e-6
        runs, current = [], []
        for i in range(n_sec + 1):
            s = -radius + 2 * radius * i / n_sec
            if surface(abs(s)) - channel(s) > tiny:
                current.append(s)
            elif current:
                runs.append(current)
                current = []
        if current:
            runs.append(current)

        for run in runs:
            pts = [(s, surface(abs(s))) for s in run]
            pts += [(s, min(channel(s), surface(abs(s)))) for s in reversed(run)]
            body += (
                f'<polygon points="{_polygon_str(pts, x_px, y_px)}" '
                'fill="#b5cbe8" stroke="#44608c" stroke-width="1.2" stroke-linejoin="round"/>'
            )

        # Red opening marks: every hopper the cut passes through.
        for ocx, ocy, w, l in openings:
            if along_x:
                on_cut, center, half = abs(cut - ocy) <= l / 2, ocx, w / 2
            else:
                on_cut, center, half = abs(cut - ocx) <= w / 2, ocy, l / 2
            if on_cut:
                body += (
                    f'<rect x="{x_px(center - half)}" y="{y_px(0) - 3}" '
                    f'width="{(x_px(center + half) - x_px(center - half)):.1f}" height="4" fill="#b03a2e"/>'
                )
        body += _dome_body(radius, dome_height, stem_wall, scale, x_px, y_px)
        label = (
            'font-size="13" font-family="system-ui, sans-serif" font-weight="600" '
            'stroke="#fff" stroke-width="3" paint-order="stroke" stroke-linejoin="round"'
        )
        # LIVE labels the widest live region at its mid-height; DEAD sits just
        # above the ground line, centered on each outer floor run (outermost
        # live extent to the wall) -- the one spot that stays inside the dead
        # region regardless of the angles that shaped it.
        if runs:
            widest = max(runs, key=lambda r: r[-1] - r[0])
            mid = (widest[0] + widest[-1]) / 2
            mid_y = (channel(mid) + surface(abs(mid))) / 2
            body += f'<text x="{x_px(mid)}" y="{y_px(mid_y)}" text-anchor="middle" fill="#2c4a7c" {label}>LIVE</text>'
            outer = max(abs(runs[0][0]), abs(runs[-1][-1]))
        else:
            outer = 0.0

        # Dashed hidden line: the dead pile's contact along the dome wall
        # BEYOND the cut plane, projected onto the section (the same collar
        # the isometric's outer skirt shows). At each horizontal position s
        # the wall point behind the plane is (s, y_w) -- or (x_w, s) for the
        # across cut -- and the dead height there is the funnel surface
        # clipped by the stored product surface (= stem wall top at the
        # wall). The collar is shortest toward the hoppers and taller
        # around the rest of the perimeter, so it reads as an arc.
        wall_top = surface(radius)
        wall_pts = []
        m = 120
        for i in range(m + 1):
            s = -radius + 2 * radius * i / m
            far = math.sqrt(max(radius * radius - s * s, 0.0))
            wx, wy = (s, far) if along_x else (far, s)
            wall_pts.append((s, min(channel_at(wx, wy), wall_top)))
        if max(h for _s, h in wall_pts) > total * 1e-6:
            body += f'<polyline points="{_polygon_str(wall_pts, x_px, y_px)}" {DASHED}/>'
        dead_mid = (outer + radius) / 2
        dead_y = y_px(0) - 6
        body += f'<text x="{x_px(-dead_mid)}" y="{dead_y}" text-anchor="middle" fill="#777" {label}>DEAD</text>'
        body += f'<text x="{x_px(dead_mid)}" y="{dead_y}" text-anchor="middle" fill="#777" {label}>DEAD</text>'
        return close(body)

    # Two perpendicular sections, side by side: along a tunnel line, and the
    # 90-degree cut across the tunnels through a hopper row.
    y_cut = 0.0 if tunnels % 2 else tunnel_spacing / 2
    x_cut = 0.0 if hoppers % 2 else hopper_spacing / 2
    elevation = _hstack([
        ("Along Tunnel", section_panel(y_cut, True)),
        ("Across Tunnels", section_panel(x_cut, False)),
    ])

    # The plan below shares the sections' horizontal scale and centerline.
    scale, x_px, _y_px, _close, width = _ground_shape_frame(radius, total, units)

    # Plan heatmap of DEAD pile depth -- the material below the funnel line,
    # min(channel height, product surface): zero over each opening, deepest
    # where the channel meets the surface, tapering to the wall. A single
    # centered opening is radially symmetric, so it renders as smooth
    # concentric bands; multi-hopper layouts rasterize on a grid (adjacent
    # same-color cells merged per row) clipped to the dome footprint.
    height_px = 2 * radius * scale + 40
    cx, cy = x_px(0.0), round(height_px / 2, 1)

    heat = ""
    if len(openings) == 1:
        def dead_depth(r):
            return min(t_dd * max(r - open_w / 2, 0.0), surface(r))

        bands = 20
        max_depth = max(dead_depth(radius * i / 200) for i in range(201)) or 1.0
        for i in range(bands, 0, -1):
            r = radius * i / bands
            r_mid = radius * (i - 0.5) / bands
            heat += (
                f'<circle cx="{cx}" cy="{cy}" r="{r * scale:.1f}" '
                f'fill="{_heat_color(dead_depth(r_mid) / max_depth)}" stroke="none"/>'
            )
    else:
        def dead_depth_xy(x, y):
            return min(channel_at(x, y), surface(math.hypot(x, y)))

        n, levels = 72, 20
        cell = 2 * radius / n
        centers = [-radius + (k + 0.5) * cell for k in range(n)]
        keep = radius + cell  # cells near the rim stay; the clip trims them
        depth_rows = [
            [dead_depth_xy(x, y) if math.hypot(x, y) <= keep else None for x in centers]
            for y in centers
        ]
        max_depth = max((d for row in depth_rows for d in row if d), default=0.0) or 1.0
        heat += (
            f'<defs><clipPath id="ld-plan-clip">'
            f'<circle cx="{cx}" cy="{cy}" r="{radius * scale:.1f}"/></clipPath></defs>'
            '<g clip-path="url(#ld-plan-clip)">'
        )
        for j, row in enumerate(depth_rows):
            y0 = cy + (centers[j] - cell / 2) * scale
            i = 0
            while i < n:
                if row[i] is None:
                    i += 1
                    continue
                idx = min(int(row[i] / max_depth * levels), levels - 1)
                i2 = i
                while i2 + 1 < n and row[i2 + 1] is not None and \
                        min(int(row[i2 + 1] / max_depth * levels), levels - 1) == idx:
                    i2 += 1
                x0 = cx + (centers[i] - cell / 2) * scale
                heat += (
                    f'<rect x="{x0:.1f}" y="{y0:.1f}" '
                    f'width="{(i2 - i + 1) * cell * scale + 0.5:.1f}" height="{cell * scale + 0.5:.1f}" '
                    f'fill="{_heat_color((idx + 0.5) / levels)}" stroke="none"/>'
                )
                i = i2 + 1
        heat += "</g>"

    for ocx, ocy, w, l in openings:
        heat += (
            f'<rect x="{cx + (ocx - w / 2) * scale:.1f}" y="{cy + (ocy - l / 2) * scale:.1f}" '
            f'width="{w * scale:.1f}" height="{l * scale:.1f}" '
            'fill="#b03a2e" stroke="#fff" stroke-width="1"/>'
        )
    heat += f'<circle cx="{cx}" cy="{cy}" r="{radius * scale:.1f}" {STRUCT_THIN}/>'
    plan = _svg(heat, width, height_px)

    multi = len(openings) > 1
    axo = _dead_pile_iso(
        core, stem_wall, dome_height, surface, t_dd, openings, units,
        n_rings=40 if multi else 30, n_spokes=80 if multi else 56,
    )
    plan_caption = (
        "Darker is deeper dead material; red marks the hopper openings"
        if multi else "Darker is deeper dead material; red is the hopper opening"
    )
    section_caption = SCALE_CAPTION + "; cut along a tunnel centerline (left) and 90&deg; across the tunnels (right)"
    return [
        ("Reclaim Sections — Live & Dead", elevation, section_caption),
        ("Plan — Dead Pile Depth", plan, plan_caption),
        ("Isometric — Dead Pile Surface", axo, "Surface of the material left after drawdown; craters are the funnels — same colors as the plan (darker is deeper dead)"),
    ]

def _dead_pile_iso(core, stem_wall, dome_height, surface_fn, t_dd, openings, units,
                   n_rings=30, n_spokes=56):
    """Axonometric surface plot of the dead pile left after drawdown, on a
    polar grid so the plot is trimmed exactly to the dome footprint: rings
    and spokes render the crater and rim smoothly, steep faces darken by
    slope for consistent cliff shading, an outer skirt closes the collar's
    face at the wall, and a faint wireframe ghost of the shell shows the
    structure in the same projection. The camera sits at a 25-degree
    elevation with a slight yaw, so the tunnel axis reads left-to-right
    (matching the Along Tunnel section) and the wall collar doesn't hide
    the crater rows behind it."""
    R, total = core["radius"], stem_wall + dome_height
    curvature = core["radius_of_curvature"]

    def rect_distance(x, y, opening):
        cx, cy, w, l = opening
        return math.hypot(max(abs(x - cx) - w / 2, 0.0), max(abs(y - cy) - l / 2, 0.0))

    def dead_z(x, y):
        channel = t_dd * min(rect_distance(x, y, o) for o in openings)
        return max(0.0, min(channel, surface_fn(math.hypot(x, y))))

    # Polar nodes: rings 0..R, spokes around the circle.
    nodes = []
    for i in range(n_rings + 1):
        r = R * i / n_rings
        ring = []
        for j in range(n_spokes):
            theta = 2 * math.pi * j / n_spokes
            x, y = r * math.cos(theta), r * math.sin(theta)
            ring.append((x, y, dead_z(x, y)))
        nodes.append(ring)
    zmax = max(z for ring in nodes for _x, _y, z in ring) or 1.0

    # Camera: 18-degree yaw (tunnels nearly horizontal on screen, a touch of
    # recession for depth), 25-degree elevation (plan depth foreshortened by
    # sin 25). u runs across the screen, w toward the viewer (painter sort).
    yaw = math.radians(18)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    elev = math.sin(math.radians(25))
    scale = 250.0 / (2 * R)
    z_scale = min(scale, 118.0 / total)
    legend_h = 58
    ox = 150.0
    oy = legend_h + 12 + max(total * z_scale, stem_wall * z_scale + R * elev * scale)

    def w_of(x, y):
        return x * sin_y + y * cos_y

    def project(x, y, z):
        return (
            round(ox + (x * cos_y - y * sin_y) * scale, 1),
            round(oy + w_of(x, y) * elev * scale - z * z_scale, 1),
        )

    # Faces use the same palette as the plan heatmap, keyed to the same
    # quantity (dead pile depth), so the two views read together: pale =
    # shallow dead, dark blue = deep. Steep crater walls darken by slope so
    # the funnels stay legible in 3D.
    ring_width = R / n_rings
    faces = []  # (depth, fill, points)

    for i in range(n_rings):
        for j in range(n_spokes):
            j2 = (j + 1) % n_spokes
            quad = [nodes[i][j], nodes[i + 1][j], nodes[i + 1][j2], nodes[i][j2]]
            zs = [p[2] for p in quad]
            mean_z = sum(zs) / 4
            slope = (max(zs) - min(zs)) / ring_width
            factor = 1.0 if slope < 0.3 else max(0.68, 1.0 - 0.10 * slope)
            fill = _heat_color(mean_z / zmax, factor)
            depth = sum(w_of(p[0], p[1]) for p in quad) / 4
            faces.append((depth, fill, [project(*p) for p in quad]))

    # Outer skirt: the collar's face at the wall, dropped to the floor.
    for j in range(n_spokes):
        j2 = (j + 1) % n_spokes
        a, b = nodes[n_rings][j], nodes[n_rings][j2]
        if max(a[2], b[2]) < zmax * 0.01:
            continue
        mean_z = (a[2] + b[2]) / 2
        fill = _heat_color(mean_z / zmax, 0.66)
        pts = [
            project(a[0], a[1], a[2]), project(b[0], b[1], b[2]),
            project(b[0], b[1], 0.0), project(a[0], a[1], 0.0),
        ]
        faces.append((w_of(a[0], a[1]) + 0.01, fill, pts))

    faces.sort(key=lambda f: f[0])
    body = ""
    for _depth, fill, pts in faces:
        point_str = " ".join(f"{px},{py}" for px, py in pts)
        body += f'<polygon points="{point_str}" fill="{fill}" stroke="{fill}" stroke-width="0.5"/>'

    # Shell rendering: a solid silhouette outline (walls + the dome's
    # visible limb) so the structure reads like it does in the sections,
    # a springline ring for the wall/dome joint, and two faint meridian
    # ribs for curvature -- meridians stay visibly curved at this low
    # camera angle where latitude circles collapse flat.
    ghost_style = 'stroke="#c9c9c9" stroke-width="1.1" fill="none" stroke-dasharray="5,4"'
    rib_style = 'stroke="#d4d4d4" stroke-width="1" fill="none"'
    sphere_center = stem_wall + dome_height - curvature

    def ring_ghost(r, z, style):
        return (
            f'<ellipse cx="{ox}" cy="{round(oy - z * z_scale, 1)}" '
            f'rx="{r * scale:.1f}" ry="{r * elev * scale:.1f}" {style}/>'
        )

    ghost = ring_ghost(R, 0.0, STRUCT_THIN)
    ghost += ring_ghost(R, stem_wall, ghost_style)

    # Meridian ribs through the apex at two plan azimuths.
    psi_max = math.acos(max(-1.0, min(1.0, (curvature - dome_height) / curvature)))
    for alpha in (math.radians(45), math.radians(135)):
        ca, sa = math.cos(alpha), math.sin(alpha)
        rib = []
        for k in range(-24, 25):
            psi = psi_max * k / 24
            r = curvature * math.sin(psi)
            z = sphere_center + curvature * math.cos(psi)
            rib.append(project(r * ca, r * sa, z))
        ghost += (
            '<polyline points="'
            + " ".join(f"{px},{py}" for px, py in rib)
            + f'" {rib_style}/>'
        )

    # Wall silhouette edges.
    u_edge = R * scale
    for side in (-1, 1):
        ghost += (
            f'<line x1="{ox + side * u_edge:.1f}" y1="{oy}" '
            f'x2="{ox + side * u_edge:.1f}" y2="{round(oy - stem_wall * z_scale, 1)}" {STRUCT_THIN}/>'
        )

    # Dome outline: the shell's visible limb from this camera. The z axis
    # is scaled independently of the plan, so it's found numerically --
    # project a dense cloud of shell points and keep the upper envelope
    # per screen column, wall top to wall top.
    n_cols = 125
    env = [None] * n_cols
    for i in range(41):
        z = stem_wall + dome_height * i / 40
        r = math.sqrt(max(curvature ** 2 - (z - sphere_center) ** 2, 0.0))
        for j in range(144):
            th = 2 * math.pi * j / 144
            px, py = project(r * math.cos(th), r * math.sin(th), z)
            c = round((px - (ox - u_edge)) / (2 * u_edge) * (n_cols - 1))
            if 0 <= c < n_cols and (env[c] is None or py < env[c]):
                env[c] = py
    outline = " ".join(
        f"{ox - u_edge + 2 * u_edge * c / (n_cols - 1):.1f},{env[c]:.1f}"
        for c in range(n_cols) if env[c] is not None
    )
    ghost += f'<polyline points="{outline}" {STRUCT_THIN}/>'
    body += ghost

    # Legend: the plan heatmap's gradient, 0 to the deepest dead pile.
    bar_x, bar_w, bar_y, bar_h, steps = 14, 120, 14, 10, 24
    for k in range(steps):
        body += (
            f'<rect x="{bar_x + bar_w * k / steps:.1f}" y="{bar_y}" '
            f'width="{bar_w / steps + 0.5:.1f}" height="{bar_h}" '
            f'fill="{_heat_color((k + 0.5) / steps)}"/>'
        )
    body += f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" fill="none" stroke="#bbb" stroke-width="0.5"/>'
    legend_text = 'font-size="11" font-family="system-ui, sans-serif" fill="#555"'
    body += f'<text x="{bar_x}" y="{bar_y + bar_h + 13}" {legend_text}>0</text>'
    body += (
        f'<text x="{bar_x + bar_w}" y="{bar_y + bar_h + 13}" text-anchor="end" {legend_text}>'
        f'{zmax:,.1f} {units}</text>'
    )
    body += f'<text x="{bar_x + bar_w + 10}" y="{bar_y + bar_h - 1}" {legend_text}>dead pile depth</text>'

    height_px = oy + R * elev * scale + 16
    return _svg(body, 300, height_px)
