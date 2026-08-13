"""Simple axonometric (3D-look) views shown beside the input diagrams.

Standard SVG tricks: circles foreshorten to ellipses (ry = rx * K), hidden
edges are dashed, the visible silhouette is solid, and a light latitude
ring hints at the surface curvature. Boxes match the input diagrams'
viewBox (300 wide) and display width so the pair sits side by side.
"""

K = 0.35  # vertical foreshortening for circles seen at a shallow angle

SOLID_STROKE = 'stroke="#333" stroke-width="2.5" stroke-linecap="round"'
SOLID = SOLID_STROKE + ' fill="none"'
HIDDEN = 'stroke="#999" stroke-width="1.2" fill="none" stroke-dasharray="5,4"'
RING = 'stroke="#bbb" stroke-width="1.2" fill="none"'
BODY_FILL = "#f4f4f4"
CUT_FILL = "#e8e8e8"


def _svg(body, view_h=205):
    return f'<svg viewBox="0 0 300 {view_h}" width="170">{body}</svg>'


def _dome_iso(base_cy, dome_h, wall_h=0, dashed_dome=False, view_h=205, rx=90.0):
    """Hemispherical dome (visual height dome_h) on an optional cylinder wall."""
    ry = rx * K
    spring_cy = base_cy - wall_h
    apex_arc = f"M{150 - rx:.1f} {spring_cy} A{rx:.1f} {dome_h} 0 0 1 {150 + rx:.1f} {spring_cy}"
    dome_style = HIDDEN if dashed_dome else SOLID

    # Filled body: dome silhouette, down the wall sides, closed by the front
    # arc of the ground ellipse.
    body = (
        f'<path d="{apex_arc} L{150 + rx:.1f} {base_cy} '
        f'A{rx:.1f} {ry:.1f} 0 0 1 {150 - rx:.1f} {base_cy} Z" fill="{BODY_FILL}" stroke="none"/>'
    )
    # Ground: front edge solid, back edge dashed only when the dome is dashed
    # (otherwise the shell hides it).
    body += f'<path d="M{150 + rx:.1f} {base_cy} A{rx:.1f} {ry:.1f} 0 0 1 {150 - rx:.1f} {base_cy}" {SOLID}/>'
    if wall_h:
        # Wall sides and the springline seam where the dome meets the wall.
        body += f'<line x1="{150 - rx:.1f}" y1="{base_cy}" x2="{150 - rx:.1f}" y2="{spring_cy}" {SOLID}/>'
        body += f'<line x1="{150 + rx:.1f}" y1="{base_cy}" x2="{150 + rx:.1f}" y2="{spring_cy}" {SOLID}/>'
        body += (
            f'<path d="M{150 + rx:.1f} {spring_cy} A{rx:.1f} {ry:.1f} 0 0 1 {150 - rx:.1f} {spring_cy}" '
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


def _cut_ellipsoid_iso(a, b, center_cy, floor_dy, view_h):
    """Full ellipsoid (visual semi-axes a, b) cut by a floor plane floor_dy
    below its center: solid above the floor, dashed below, shaded cut face."""
    floor_cy = center_cy + floor_dy
    fr = a * max(0.0, 1 - (floor_dy / b) ** 2) ** 0.5
    fry = fr * K

    body = f'<ellipse cx="150" cy="{center_cy}" rx="{a:.1f}" ry="{b:.1f}" {HIDDEN}/>'
    body += (
        f'<clipPath id="above-floor"><rect x="0" y="0" width="300" height="{floor_cy:.1f}"/></clipPath>'
        f'<ellipse cx="150" cy="{center_cy}" rx="{a:.1f}" ry="{b:.1f}" '
        f'clip-path="url(#above-floor)" fill="{BODY_FILL}" {SOLID_STROKE}/>'
    )
    # Cut face (the floor slice) reads as a shaded ellipse with a solid rim.
    body += (
        f'<ellipse cx="150" cy="{floor_cy:.1f}" rx="{fr:.1f}" ry="{fry:.1f}" '
        f'fill="{CUT_FILL}" stroke="#333" stroke-width="1.5"/>'
    )
    return _svg(body, view_h)


def spherical():
    return _dome_iso(base_cy=160, dome_h=72)


def ellipsoid():
    return _dome_iso(base_cy=150, dome_h=42)


def vertical_ellipsoid():
    # Default proportions: floor slightly below the equator.
    return _cut_ellipsoid_iso(a=48, b=62, center_cy=85, floor_dy=10, view_h=170)


def horizontal_ellipsoid():
    return _cut_ellipsoid_iso(a=88, b=40, center_cy=100, floor_dy=8, view_h=160)


def ellipse2d():
    # A flat disc seen at an angle, with its axes dashed.
    body = (
        f'<ellipse cx="150" cy="95" rx="95" ry="33" fill="{BODY_FILL}" '
        'stroke="#333" stroke-width="2.5"/>'
        f'<line x1="55" y1="95" x2="245" y2="95" {HIDDEN}/>'
        f'<line x1="150" y1="62" x2="150" y2="128" {HIDDEN}/>'
        '<circle cx="150" cy="95" r="2.5" fill="#333"/>'
    )
    return _svg(body, view_h=180)


def dry_bulk_calculator():
    return _dome_iso(base_cy=160, dome_h=62, wall_h=25)


def dry_bulk_sizer():
    return _dome_iso(base_cy=160, dome_h=62, wall_h=25, dashed_dome=True)
