"""Simple axonometric (3D-look) views shown beside the input diagrams.

Standard SVG tricks: circles foreshorten to ellipses (ry = rx * K), hidden
edges are dashed, the visible silhouette is solid, and a light latitude
ring hints at the surface curvature. Boxes match the input diagrams'
viewBox (300 wide) and display width so the pair sits side by side.

True proportions: K implies a camera elevation (sin = K), so heights are
drawn with the matching cos factor at the same scale as the plan, and each
view is built from its calculator's default dimensions -- the picture
matches the shape being modeled (a hemisphere looks like a hemisphere).
Views fit their box by shrinking uniformly, never by squashing heights.
"""

K = 0.35  # vertical foreshortening for circles seen at a shallow angle
COS_E = (1 - K * K) ** 0.5  # cos of the camera elevation implied by K

SOLID_STROKE = 'stroke="#333" stroke-width="2.5" stroke-linecap="round"'
SOLID = SOLID_STROKE + ' fill="none"'
HIDDEN = 'stroke="#999" stroke-width="1.2" fill="none" stroke-dasharray="5,4"'
RING = 'stroke="#bbb" stroke-width="1.2" fill="none"'
BODY_FILL = "#f4f4f4"
CUT_FILL = "#e8e8e8"


def _svg(body, view_h=205):
    return f'<svg viewBox="0 0 300 {view_h}" width="170">{body}</svg>'


def _dome_iso(height_ratio, wall_ratio=0.0, dashed_dome=False, view_h=205):
    """Dome of world height = height_ratio x floor radius, on an optional
    wall of wall_ratio x floor radius, at true camera proportions."""
    base_cy = 160.0
    budget = base_cy - 12  # room above the base line
    rx = min(95.0, budget / max((height_ratio + wall_ratio) * COS_E, 0.01))
    dome_h = rx * height_ratio * COS_E
    wall_h = rx * wall_ratio * COS_E
    ry = rx * K
    spring_cy = base_cy - wall_h
    apex_arc = f"M{150 - rx:.1f} {spring_cy:.1f} A{rx:.1f} {dome_h:.1f} 0 0 1 {150 + rx:.1f} {spring_cy:.1f}"
    dome_style = HIDDEN if dashed_dome else SOLID

    # Filled body: dome silhouette, down the wall sides, closed by the front
    # arc of the ground ellipse.
    body = (
        f'<path d="{apex_arc} L{150 + rx:.1f} {base_cy:.1f} '
        f'A{rx:.1f} {ry:.1f} 0 0 1 {150 - rx:.1f} {base_cy:.1f} Z" fill="{BODY_FILL}" stroke="none"/>'
    )
    # Ground: front edge solid, back edge dashed only when the dome is dashed
    # (otherwise the shell hides it).
    body += f'<path d="M{150 + rx:.1f} {base_cy:.1f} A{rx:.1f} {ry:.1f} 0 0 1 {150 - rx:.1f} {base_cy:.1f}" {SOLID}/>'
    if wall_h:
        # Wall sides and the springline seam where the dome meets the wall.
        body += f'<line x1="{150 - rx:.1f}" y1="{base_cy:.1f}" x2="{150 - rx:.1f}" y2="{spring_cy:.1f}" {SOLID}/>'
        body += f'<line x1="{150 + rx:.1f}" y1="{base_cy:.1f}" x2="{150 + rx:.1f}" y2="{spring_cy:.1f}" {SOLID}/>'
        body += (
            f'<path d="M{150 + rx:.1f} {spring_cy:.1f} A{rx:.1f} {ry:.1f} 0 0 1 {150 - rx:.1f} {spring_cy:.1f}" '
            f'stroke="#666" stroke-width="1.2" fill="none"/>'
        )
    body += f'<path d="{apex_arc}" {dome_style}/>'
    if not dashed_dome:
        # Latitude ring at half the dome height for curvature.
        lat_r = rx * (1 - 0.25) ** 0.5
        body += (
            f'<ellipse cx="150" cy="{spring_cy - dome_h * 0.5:.1f}" '
            f'rx="{lat_r:.1f}" ry="{lat_r * K:.1f}" {RING}/>'
        )
    return _svg(body, view_h)


def _cut_ellipsoid_iso(a_w, b_w, height_w, center_cy, view_h):
    """Full ellipsoid (world semi-axes a_w horizontal, b_w vertical) cut by
    a floor plane so the dome stands height_w above it: solid above the
    floor, dashed below, shaded cut face. Screen axes keep the true ratio
    (vertical scaled by COS_E)."""
    a = min(88.0, (center_cy - 12) / max((b_w / a_w) * COS_E, 0.01))
    b = a * (b_w / a_w) * COS_E
    floor_dy = (height_w - b_w) / a_w * a * COS_E  # floor below center when +
    floor_cy = center_cy + floor_dy
    fr_w = a_w * max(0.0, 1 - ((height_w - b_w) / b_w) ** 2) ** 0.5
    fr = fr_w / a_w * a
    fry = fr * K

    body = f'<ellipse cx="150" cy="{center_cy:.1f}" rx="{a:.1f}" ry="{b:.1f}" {HIDDEN}/>'
    body += (
        f'<clipPath id="above-floor"><rect x="0" y="0" width="300" height="{floor_cy:.1f}"/></clipPath>'
        f'<ellipse cx="150" cy="{center_cy:.1f}" rx="{a:.1f}" ry="{b:.1f}" '
        f'clip-path="url(#above-floor)" fill="{BODY_FILL}" {SOLID_STROKE}/>'
    )
    # Cut face (the floor slice) reads as a shaded ellipse with a solid rim.
    body += (
        f'<ellipse cx="150" cy="{floor_cy:.1f}" rx="{fr:.1f}" ry="{fry:.1f}" '
        f'fill="{CUT_FILL}" stroke="#333" stroke-width="1.5"/>'
    )
    return _svg(body, view_h)


# Each view uses the same world proportions as its companion input diagram
# (the front view beside it), so the pair reads as one shape from two angles.


def spherical():
    # Hemisphere, matching the diagram and shape card.
    return _dome_iso(height_ratio=1.0)


def ellipsoid():
    # Oblate half-ellipsoid, height/radius = 40/90 like the diagram.
    return _dome_iso(height_ratio=40.0 / 90.0)


def vertical_ellipsoid():
    # Tall ellipse (50 x 62 like the diagram), floor 40 below the center.
    return _cut_ellipsoid_iso(a_w=50.0, b_w=62.0, height_w=102.0, center_cy=80, view_h=170)


def horizontal_ellipsoid():
    # Wide ellipse (105 x 48 like the diagram), floor 30 below the center.
    return _cut_ellipsoid_iso(a_w=105.0, b_w=48.0, height_w=78.0, center_cy=70, view_h=160)


def ellipse2d():
    # A flat disc seen at an angle, with its axes dashed (ry = rx * K is the
    # true look of a flat circle at this camera; nothing to correct).
    body = (
        f'<ellipse cx="150" cy="95" rx="95" ry="33" fill="{BODY_FILL}" '
        'stroke="#333" stroke-width="2.5"/>'
        f'<line x1="55" y1="95" x2="245" y2="95" {HIDDEN}/>'
        f'<line x1="150" y1="62" x2="150" y2="128" {HIDDEN}/>'
        '<circle cx="150" cy="95" r="2.5" fill="#333"/>'
    )
    return _svg(body, view_h=180)


def dry_bulk_calculator():
    # Hemisphere on a stem wall about half the floor radius -- representative
    # of the storage calculators' defaults.
    return _dome_iso(height_ratio=1.0, wall_ratio=0.5)


def dry_bulk_sizer():
    return _dome_iso(height_ratio=1.0, wall_ratio=0.5, dashed_dome=True)
