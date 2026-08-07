import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geometry import ellipse, ellipsoid_dome, horizontal_ellipsoid_dome, spherical_dome, vertical_ellipsoid_dome


def _section(result, title):
    for section_title, rows in result:
        if section_title == title:
            return rows
    raise KeyError(title)


def _value(rows, label):
    for row_label, value, _power in rows:
        if row_label == label:
            return value
    raise KeyError(label)


def test_spherical_hemisphere_matches_known_formulas():
    diameter = 100.0
    radius = diameter / 2
    result = spherical_dome(diameter=diameter, height=radius, stem_wall=0)
    dome = _section(result, "Dome")

    assert math.isclose(_value(dome, "Radius of Curvature"), radius, rel_tol=1e-9)
    assert math.isclose(_value(dome, "Surface Area"), 2 * math.pi * radius ** 2, rel_tol=1e-9)
    assert math.isclose(_value(dome, "Volume"), (2 / 3) * math.pi * radius ** 3, rel_tol=1e-9)


def test_spherical_stem_wall_adds_cylinder_volume():
    diameter = 100.0
    radius = diameter / 2
    stem_wall = 10.0
    with_wall = _section(spherical_dome(diameter=diameter, height=radius, stem_wall=stem_wall), "Dome")
    without_wall = _section(spherical_dome(diameter=diameter, height=radius, stem_wall=0), "Dome")

    cylinder_volume = math.pi * radius ** 2 * stem_wall
    assert math.isclose(
        _value(with_wall, "Volume"),
        _value(without_wall, "Volume") + cylinder_volume,
        rel_tol=1e-9,
    )
    assert math.isclose(_value(with_wall, "Total Height"), radius + stem_wall)


def test_spherical_reference_example_from_monolithic_dome_institute():
    # diameter=105, height=35 -- cross-checked against the published
    # Spherical Dome Calculator (values rounded to 2 decimals on their site).
    result = spherical_dome(diameter=105.0, height=35.0, stem_wall=0)
    floor, dome = _section(result, "Floor"), _section(result, "Dome")

    assert math.isclose(_value(floor, "Circumference"), 329.87, rel_tol=1e-3)
    assert math.isclose(_value(floor, "Area"), 8659.01, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Radius of Curvature"), 56.88, rel_tol=1e-3)


def test_ellipsoid_oblate_reference_example_from_monolithic_dome_institute():
    # diameter=50, height=20 (oblate, a=25 > b=20) -- cross-checked against
    # the published Ellipsoid Dome Calculator.
    dome = _section(ellipsoid_dome(diameter=50.0, height=20.0, stem_wall=0), "Dome")

    assert math.isclose(_value(dome, "Ellipticity Ratio"), 1.25, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Curvature"), 31.25, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Surface Distance"), 35.45, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Surface Area"), 3415.22, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Volume"), 26179.94, rel_tol=1e-3)


def test_ellipsoid_reduces_to_sphere_when_axes_equal():
    diameter = 100.0
    radius = diameter / 2
    ellipsoid_dome_result = _section(ellipsoid_dome(diameter=diameter, height=radius, stem_wall=0), "Dome")
    sphere_dome_result = _section(spherical_dome(diameter=diameter, height=radius, stem_wall=0), "Dome")

    assert math.isclose(
        _value(ellipsoid_dome_result, "Surface Area"),
        _value(sphere_dome_result, "Surface Area"),
        rel_tol=1e-6,
    )
    assert math.isclose(
        _value(ellipsoid_dome_result, "Volume"),
        _value(sphere_dome_result, "Volume"),
        rel_tol=1e-6,
    )


def test_vertical_ellipsoid_reference_example_from_monolithic_dome_institute():
    # horizontal=25, vertical=16.5, height=20 (floor below the equator) --
    # cross-checked against the published Vertical Ellipsoid Dome Calculator.
    result = vertical_ellipsoid_dome(horizontal=25.0, vertical=16.5, height=20.0)
    floor, dome = _section(result, "Floor"), _section(result, "Dome")

    assert math.isclose(_value(floor, "Radius"), 24.43, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Ellipticity Ratio"), 1.52, rel_tol=1e-2)
    assert math.isclose(_value(dome, "Curvature"), 37.88, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Surface Distance"), 36.50, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Surface Area"), 3629.56, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Volume"), 28367.61, rel_tol=1e-3)


def test_vertical_ellipsoid_matches_ellipsoid_dome_when_floor_at_equator():
    # When height == vertical radius, the floor sits exactly at the equator,
    # which is the same shape as the (horizontal) Ellipsoid dome.
    horizontal, vertical = 30.0, 18.0
    vertical_dome = _section(
        vertical_ellipsoid_dome(horizontal=horizontal, vertical=vertical, height=vertical), "Dome"
    )
    ellipsoid_dome_result = _section(
        ellipsoid_dome(diameter=2 * horizontal, height=vertical, stem_wall=0), "Dome"
    )

    assert math.isclose(
        _value(vertical_dome, "Surface Area"), _value(ellipsoid_dome_result, "Surface Area"), rel_tol=1e-6
    )
    assert math.isclose(_value(vertical_dome, "Volume"), _value(ellipsoid_dome_result, "Volume"), rel_tol=1e-6)


def test_horizontal_ellipsoid_reference_example_from_monolithic_dome_institute():
    # major=25, minor=16.5, height=20 -- cross-checked against the published
    # Horizontal Ellipsoid Dome Calculator. That calculator itself only
    # claims 4-6 significant digits (it also integrates numerically), so a
    # slightly looser tolerance is used for volume/surface area.
    result = horizontal_ellipsoid_dome(major=25.0, minor=16.5, height=20.0)
    floor, dome = _section(result, "Floor Ellipse"), _section(result, "Dome")

    assert math.isclose(_value(floor, "Major Diameter"), 48.86, rel_tol=1e-3)
    assert math.isclose(_value(floor, "Minor Diameter"), 32.25, rel_tol=1e-3)
    assert math.isclose(_value(floor, "Perimeter"), 128.75, rel_tol=1e-3)
    assert math.isclose(_value(floor, "Area"), 1237.60, rel_tol=1e-3)
    assert math.isclose(_value(floor, "Foci (±)"), 18.35, rel_tol=1e-3)

    assert math.isclose(_value(dome, "Ellipticity Ratio"), 0.66, rel_tol=1e-2)
    assert math.isclose(_value(dome, "Surface Distance"), 36.50, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Surface Area"), 2784.15, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Volume"), 18722.57, rel_tol=1e-3)


def test_horizontal_ellipsoid_hemisphere_matches_spherical_dome():
    # When major == minor and height == minor (floor at the equator), a
    # horizontal ellipsoid is just a sphere -- same as the Spherical dome.
    radius = 20.0
    horizontal_dome = _section(
        horizontal_ellipsoid_dome(major=radius, minor=radius, height=radius), "Dome"
    )
    spherical_dome_result = _section(spherical_dome(diameter=2 * radius, height=radius, stem_wall=0), "Dome")

    assert math.isclose(_value(horizontal_dome, "Volume"), _value(spherical_dome_result, "Volume"), rel_tol=1e-3)
    assert math.isclose(
        _value(horizontal_dome, "Surface Area"), _value(spherical_dome_result, "Surface Area"), rel_tol=1e-3
    )


def test_ellipse_reference_example_from_monolithic_dome_institute():
    # major=30, minor=20 -- cross-checked against the published Ellipse Calculator.
    rows = _section(ellipse(major=30.0, minor=20.0), "Ellipse")

    assert math.isclose(_value(rows, "Circumference"), 158.65, rel_tol=1e-3)
    assert math.isclose(_value(rows, "Curvature"), 45.00, rel_tol=1e-3)
    assert math.isclose(_value(rows, "Area"), 1884.96, rel_tol=1e-3)
    assert math.isclose(_value(rows, "Foci (±)"), 22.36, rel_tol=1e-3)


def test_ellipse_circle_matches_known_formulas():
    radius = 12.0
    rows = _section(ellipse(major=radius, minor=radius), "Ellipse")

    assert math.isclose(_value(rows, "Circumference"), 2 * math.pi * radius, rel_tol=1e-9)
    assert math.isclose(_value(rows, "Area"), math.pi * radius ** 2, rel_tol=1e-9)
    assert math.isclose(_value(rows, "Foci (±)"), 0.0, abs_tol=1e-9)
