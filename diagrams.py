"""Annotated SVG diagrams shown on the dimension-entry step.

Each diagram labels the shape's input fields with dimension arrows so the
user can see what each number measures. Structure is drawn in dark gray,
dimension annotations in blue, reference/extension lines dashed light gray.
"""

STRUCT = 'stroke="#333" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"'
DIM = 'stroke="#0b72b9" stroke-width="1.5" fill="none"'
EXT = 'stroke="#aaa" stroke-width="1" stroke-dasharray="4,3"'
# paint-order+white stroke gives labels a knockout halo, so structure lines
# appear to break behind text instead of cutting through it.
TEXT = (
    'font-size="16" font-family="system-ui, sans-serif" fill="#0b72b9" '
    'stroke="#fff" stroke-width="4" paint-order="stroke" stroke-linejoin="round"'
)

ARROW_DEFS = (
    '<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
    'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#0b72b9"/></marker></defs>'
)


def _svg(body, width=170, view_h=205):
    return f'<svg viewBox="0 0 300 {view_h}" width="{width}">{ARROW_DEFS}{body}</svg>'


def _hdim(x1, x2, y, label):
    mid = (x1 + x2) / 2
    return (
        f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" {DIM} marker-start="url(#arr)" marker-end="url(#arr)"/>'
        f'<text x="{mid}" y="{y + 16}" text-anchor="middle" {TEXT}>{label}</text>'
    )


def _vdim(x, y1, y2, label, side=1):
    lx = x + 12 * side
    my = (y1 + y2) / 2
    return (
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" {DIM} marker-start="url(#arr)" marker-end="url(#arr)"/>'
        f'<text transform="rotate(-90 {lx} {my})" x="{lx}" y="{my}" text-anchor="middle" '
        f'dominant-baseline="middle" {TEXT}>{label}</text>'
    )


def _radius_arrow(cx, cy, x2, y2):
    return f'<line x1="{cx}" y1="{cy}" x2="{x2}" y2="{y2}" {DIM} marker-end="url(#arr)"/>'


def _ext(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {EXT}/>'


def _center_dot(cx, cy):
    return f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="#333"/>'


def _dome_structure(arc_path, ground_y=160, wall_top=120):
    return (
        f'<line x1="25" y1="{ground_y}" x2="275" y2="{ground_y}" {STRUCT}/>'
        f'<line x1="60" y1="{ground_y}" x2="60" y2="{wall_top}" {STRUCT}/>'
        f'<line x1="240" y1="{ground_y}" x2="240" y2="{wall_top}" {STRUCT}/>'
        f'<path d="{arc_path}" {STRUCT}/>'
    )


def _dome_diagram(arc_path, apex_y):
    """Diameter / Height / Stem Wall annotations shared by the round-based domes."""
    body = _dome_structure(arc_path)
    body += _hdim(60, 240, 180, "Diameter")
    body += _ext(150, apex_y, 257, apex_y) + _ext(43, 120, 257, 120)
    body += _vdim(257, apex_y, 120, "Height")
    body += _vdim(43, 120, 160, "Stem Wall", side=-1)
    return _svg(body)


def spherical():
    # Hemisphere (r=90 on the 60..240 base), matching the shape card.
    return _dome_diagram(HEMI_ARC, apex_y=30)


def ellipsoid():
    return _dome_diagram("M60 120 A 90 40 0 0 1 240 120", apex_y=80)


def vertical_ellipsoid():
    body = (
        f'<line x1="40" y1="130" x2="255" y2="130" {STRUCT}/>'
        f'<ellipse cx="150" cy="90" rx="50" ry="62" {STRUCT}/>'
    )
    body += _center_dot(150, 90)
    body += _radius_arrow(150, 90, 200, 90)
    body += f'<text x="174" y="106" text-anchor="middle" {TEXT}>Horizontal</text>'
    body += _radius_arrow(150, 90, 150, 28)
    body += (
        f'<text transform="rotate(-90 138 59)" x="138" y="59" text-anchor="middle" '
        f'dominant-baseline="middle" {TEXT}>Vertical</text>'
    )
    body += _ext(150, 28, 250, 28)
    body += _vdim(250, 28, 130, "Height")
    return _svg(body, view_h=170)


def horizontal_ellipsoid():
    body = (
        f'<line x1="20" y1="125" x2="270" y2="125" {STRUCT}/>'
        f'<ellipse cx="150" cy="95" rx="105" ry="48" {STRUCT}/>'
    )
    body += _center_dot(150, 95)
    body += _radius_arrow(150, 95, 255, 95)
    body += f'<text x="202" y="88" text-anchor="middle" {TEXT}>Major</text>'
    body += _radius_arrow(150, 95, 150, 47)
    body += (
        f'<text transform="rotate(-90 138 71)" x="138" y="71" text-anchor="middle" '
        f'dominant-baseline="middle" {TEXT}>Minor</text>'
    )
    body += _ext(150, 47, 262, 47)
    body += _vdim(262, 47, 125, "Height")
    return _svg(body, view_h=160)


def ellipse2d():
    body = f'<ellipse cx="150" cy="100" rx="110" ry="62" {STRUCT}/>'
    body += _center_dot(150, 100)
    body += _radius_arrow(150, 100, 260, 100)
    body += f'<text x="205" y="92" text-anchor="middle" {TEXT}>Major Radius</text>'
    body += _radius_arrow(150, 100, 150, 38)
    body += (
        f'<text transform="rotate(-90 138 69)" x="138" y="69" text-anchor="middle" '
        f'dominant-baseline="middle" {TEXT}>Minor Radius</text>'
    )
    return _svg(body, view_h=180)


# Bulk storage schematic geometry: hemisphere shell of radius 90 on the
# 60..240 base (apex y=30), matching the shape cards. The pile (drawn on an
# inner shell of radius 88 so it sits inside the stroke) bears up the stem
# wall and along the dome wall to where a 30-degree repose line from the
# peak meets the shell: peak (150,45) leaves a visible freeboard gap below
# the apex, and the 30-degree line meets r=88 at (150 +- 83.9, 93.4)
# (rise 48.4 over run 83.9 = 30 degrees each side).
HEMI_ARC = "M60 120 A 90 90 0 0 1 240 120"


def _pile_with_angle_and_freeboard(apex_y=30, peak_y=45):
    parts = (
        '<path d="M62 158 L62 120 A88 88 0 0 1 66.1 93.4 L150 45 L233.9 93.4 '
        'A88 88 0 0 1 238 120 L238 158 Z" fill="#ddd" stroke="#666" stroke-width="1"/>'
    )
    parts += _ext(66, 93.4, 112, 93.4)
    parts += f'<path d="M96 93.4 A 30 30 0 0 0 92 78.4" {DIM}/>'
    parts += f'<text x="101" y="88" text-anchor="start" {TEXT}>Angle</text>'
    parts += _vdim(150, apex_y, peak_y, "", side=1)
    parts += f'<text x="150" y="{apex_y - 9}" text-anchor="middle" {TEXT}>Freeboard</text>'
    return parts


def dry_bulk_calculator():
    body = _dome_structure(HEMI_ARC)
    body += _pile_with_angle_and_freeboard()
    body += _hdim(60, 240, 180, "Diameter")
    body += _ext(43, 120, 257, 120) + _ext(150, 30, 257, 30)
    body += _vdim(257, 30, 120, "Height")
    body += _vdim(43, 120, 160, "Stem Wall", side=-1)
    return _svg(body)


def live_dead():
    """Bulk calculator schematic plus the reclaim inputs: a hopper opening in
    the floor and the drawdown funnel rising from its edges. The funnel lines
    from (145,158)/(155,158) at ~70 degrees meet the 30-degree pile surface
    at (111.9, 67.1) and (188.1, 67.1)."""
    body = _dome_structure(HEMI_ARC)
    body += _pile_with_angle_and_freeboard()
    body += (
        '<polygon points="145,158 111.9,67.1 150,45 188.1,67.1 155,158" '
        'fill="#b5cbe8" fill-opacity="0.75" stroke="#44608c" stroke-width="1.5" stroke-linejoin="round"/>'
    )
    body += '<rect x="144" y="155" width="12" height="5" fill="#b03a2e"/>'
    body += f'<text x="163" y="152" text-anchor="start" {TEXT}>Opening</text>'
    body += _ext(165, 130, 205, 130)
    body += f'<path d="M185 130 A 20 20 0 0 0 171.8 111.2" {DIM}/>'
    body += f'<text x="190" y="120" text-anchor="start" {TEXT}>Drawdown</text>'
    body += _hdim(60, 240, 180, "Diameter")
    body += _ext(43, 120, 257, 120) + _ext(150, 30, 257, 30)
    body += _vdim(257, 30, 120, "Height")
    body += _vdim(43, 120, 160, "Stem Wall", side=-1)
    return _svg(body)


def dry_bulk_sizer():
    body = (
        f'<line x1="25" y1="160" x2="275" y2="160" {STRUCT}/>'
        f'<line x1="60" y1="160" x2="60" y2="120" {STRUCT}/>'
        f'<line x1="240" y1="160" x2="240" y2="120" {STRUCT}/>'
        f'<path d="{HEMI_ARC}" {STRUCT} stroke-dasharray="6,5"/>'
    )
    body += _pile_with_angle_and_freeboard()
    body += f'<text x="150" y="140" text-anchor="middle" font-size="15" font-family="system-ui, sans-serif" fill="#555">Capacity</text>'
    body += _vdim(43, 120, 160, "Stem Wall", side=-1)
    body += (
        f'<text x="150" y="196" text-anchor="middle" font-size="13" font-family="system-ui, sans-serif" '
        f'fill="#888">dome size is calculated from capacity</text>'
    )
    return _svg(body)
