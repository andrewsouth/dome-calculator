"""Annotated SVG diagrams shown on the dimension-entry step.

Each diagram labels the shape's input fields with dimension arrows so the
user can see what each number measures. Structure is drawn in dark gray,
dimension annotations in blue, reference/extension lines dashed light gray.
"""

STRUCT = 'stroke="#333" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"'
DIM = 'stroke="#0b72b9" stroke-width="1.5" fill="none"'
EXT = 'stroke="#aaa" stroke-width="1" stroke-dasharray="4,3"'
TEXT = 'font-size="16" font-family="system-ui, sans-serif" fill="#0b72b9"'

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
    body += _ext(150, apex_y, 257, apex_y) + _ext(243, 120, 257, 120)
    body += _vdim(257, apex_y, 120, "Height")
    body += _vdim(43, 120, 160, "Stem Wall", side=-1)
    return _svg(body)


def spherical():
    return _dome_diagram("M60 120 A 94.81 94.81 0 0 1 240 120", apex_y=55)


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


def _pile_with_angle_and_freeboard(apex_y=55, peak_y=80):
    """Gray material pile (fills against walls, cone on top), angle-of-repose
    arc at the cone's left base, and a freeboard gap dimension at the apex."""
    parts = (
        f'<polygon points="62,158 238,158 238,108 150,{peak_y} 62,108" '
        'fill="#ddd" stroke="#666" stroke-width="1"/>'
    )
    parts += _ext(62, 108, 105, 108)
    parts += f'<path d="M90 108 A 28 28 0 0 0 88.7 99.5" {DIM}/>'
    parts += f'<text x="97" y="102" text-anchor="start" {TEXT}>Angle</text>'
    parts += _vdim(150, apex_y, peak_y, "", side=1)
    parts += f'<text x="150" y="{apex_y - 11}" text-anchor="middle" {TEXT}>Freeboard</text>'
    return parts


def dry_bulk_calculator():
    body = _dome_structure("M60 120 A 94.81 94.81 0 0 1 240 120")
    body += _pile_with_angle_and_freeboard()
    body += _hdim(60, 240, 180, "Diameter")
    body += _ext(243, 120, 257, 120)
    body += _vdim(257, 55, 120, "Height")
    body += _vdim(43, 120, 160, "Stem Wall", side=-1)
    return _svg(body)


def dry_bulk_sizer():
    body = (
        f'<line x1="25" y1="160" x2="275" y2="160" {STRUCT}/>'
        f'<line x1="60" y1="160" x2="60" y2="120" {STRUCT}/>'
        f'<line x1="240" y1="160" x2="240" y2="120" {STRUCT}/>'
        f'<path d="M60 120 A 94.81 94.81 0 0 1 240 120" {STRUCT} stroke-dasharray="6,5"/>'
    )
    body += _pile_with_angle_and_freeboard()
    body += f'<text x="150" y="140" text-anchor="middle" font-size="15" font-family="system-ui, sans-serif" fill="#555">Capacity</text>'
    body += _vdim(43, 120, 160, "Stem Wall", side=-1)
    body += (
        f'<text x="150" y="196" text-anchor="middle" font-size="13" font-family="system-ui, sans-serif" '
        f'fill="#888">dome size is calculated from capacity</text>'
    )
    return _svg(body)
