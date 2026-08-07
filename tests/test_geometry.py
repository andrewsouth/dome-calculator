import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geometry import ellipsoid_dome, spherical_dome, vertical_ellipsoid_dome


def _value(rows, label):
    for row_label, value, _power in rows:
        if row_label == label:
            return value
    raise KeyError(label)


def test_spherical_hemisphere_matches_known_formulas():
    diameter = 100.0
    radius = diameter / 2
    result = spherical_dome(diameter=diameter, height=radius, stem_wall=0)

    assert math.isclose(_value(result["dome"], "Radius of Curvature"), radius, rel_tol=1e-9)
    assert math.isclose(_value(result["dome"], "Surface Area"), 2 * math.pi * radius ** 2, rel_tol=1e-9)
    assert math.isclose(_value(result["dome"], "Volume"), (2 / 3) * math.pi * radius ** 3, rel_tol=1e-9)


def test_spherical_stem_wall_adds_cylinder_volume():
    diameter = 100.0
    radius = diameter / 2
    stem_wall = 10.0
    with_wall = spherical_dome(diameter=diameter, height=radius, stem_wall=stem_wall)
    without_wall = spherical_dome(diameter=diameter, height=radius, stem_wall=0)

    cylinder_volume = math.pi * radius ** 2 * stem_wall
    assert math.isclose(
        _value(with_wall["dome"], "Volume"),
        _value(without_wall["dome"], "Volume") + cylinder_volume,
        rel_tol=1e-9,
    )
    assert math.isclose(_value(with_wall["dome"], "Total Height"), radius + stem_wall)


def test_spherical_reference_example_from_monolithic_dome_institute():
    # diameter=105, height=35 -- cross-checked against the published
    # Spherical Dome Calculator (values rounded to 2 decimals on their site).
    result = spherical_dome(diameter=105.0, height=35.0, stem_wall=0)

    assert math.isclose(_value(result["floor"], "Circumference"), 329.87, rel_tol=1e-3)
    assert math.isclose(_value(result["floor"], "Area"), 8659.01, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Radius of Curvature"), 56.88, rel_tol=1e-3)


def test_ellipsoid_oblate_reference_example_from_monolithic_dome_institute():
    # diameter=50, height=20 (oblate, a=25 > b=20) -- cross-checked against
    # the published Ellipsoid Dome Calculator.
    result = ellipsoid_dome(diameter=50.0, height=20.0, stem_wall=0)

    assert math.isclose(_value(result["dome"], "Ellipticity Ratio"), 1.25, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Curvature"), 31.25, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Surface Distance"), 35.45, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Surface Area"), 3415.22, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Volume"), 26179.94, rel_tol=1e-3)


def test_ellipsoid_reduces_to_sphere_when_axes_equal():
    diameter = 100.0
    radius = diameter / 2
    ellipsoid_result = ellipsoid_dome(diameter=diameter, height=radius, stem_wall=0)
    sphere_result = spherical_dome(diameter=diameter, height=radius, stem_wall=0)

    assert math.isclose(
        _value(ellipsoid_result["dome"], "Surface Area"),
        _value(sphere_result["dome"], "Surface Area"),
        rel_tol=1e-6,
    )
    assert math.isclose(
        _value(ellipsoid_result["dome"], "Volume"),
        _value(sphere_result["dome"], "Volume"),
        rel_tol=1e-6,
    )


def test_vertical_ellipsoid_reference_example_from_monolithic_dome_institute():
    # horizontal=25, vertical=16.5, height=20 (floor below the equator) --
    # cross-checked against the published Vertical Ellipsoid Dome Calculator.
    result = vertical_ellipsoid_dome(horizontal=25.0, vertical=16.5, height=20.0)

    assert math.isclose(_value(result["floor"], "Radius"), 24.43, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Ellipticity Ratio"), 1.52, rel_tol=1e-2)
    assert math.isclose(_value(result["dome"], "Curvature"), 37.88, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Surface Distance"), 36.50, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Surface Area"), 3629.56, rel_tol=1e-3)
    assert math.isclose(_value(result["dome"], "Volume"), 28367.61, rel_tol=1e-3)


def test_vertical_ellipsoid_matches_ellipsoid_dome_when_floor_at_equator():
    # When height == vertical radius, the floor sits exactly at the equator,
    # which is the same shape as the (horizontal) Ellipsoid dome.
    horizontal, vertical = 30.0, 18.0
    vertical_result = vertical_ellipsoid_dome(horizontal=horizontal, vertical=vertical, height=vertical)
    ellipsoid_result = ellipsoid_dome(diameter=2 * horizontal, height=vertical, stem_wall=0)

    assert math.isclose(
        _value(vertical_result["dome"], "Surface Area"),
        _value(ellipsoid_result["dome"], "Surface Area"),
        rel_tol=1e-6,
    )
    assert math.isclose(
        _value(vertical_result["dome"], "Volume"),
        _value(ellipsoid_result["dome"], "Volume"),
        rel_tol=1e-6,
    )
