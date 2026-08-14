import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geometry import (
    dry_bulk_storage_dome,
    dry_bulk_storage_sizer,
    ellipse,
    ellipsoid_dome,
    horizontal_ellipsoid_dome,
    spherical_dome,
    vertical_ellipsoid_dome,
)


def _section(result, title):
    for section_title, rows in result:
        if section_title == title:
            return rows
    raise KeyError(title)


def _section_starting_with(result, prefix):
    for section_title, rows in result:
        if section_title.startswith(prefix):
            return rows
    raise KeyError(prefix)


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


def test_dry_bulk_calculator_reference_example_from_monolithic_dome_institute():
    # diameter=116, height=58, stem_wall=36, angle=32, density=50 lbs/ft3 --
    # cross-checked against the published Dry Bulk Storage Dome Calculator.
    result = dry_bulk_storage_dome(
        diameter=116.0, height=58.0, stem_wall=36.0,
        angle_degrees=32.0, density=50.0, density_unit="lbs/ft3", length_unit="ft",
    )
    product = _section(result, "Product")
    cone = _section_starting_with(result, "Cone @")
    portion = _section(result, "Portion above cone")
    frustum = _section(result, "Frustum below cone")
    total = _section_starting_with(result, "Total:")

    assert math.isclose(_value(product, "Volume"), 724652.76, rel_tol=1e-3)
    assert math.isclose(_value(product, "Capacity"), 18116.32, rel_tol=1e-3)

    assert math.isclose(_value(cone, "Radius"), 52.13, rel_tol=1e-3)
    assert math.isclose(_value(cone, "Height"), 32.57, rel_tol=1e-3)
    assert math.isclose(_value(cone, "Slant Length"), 61.47, rel_tol=1e-3)
    assert math.isclose(_value(cone, "Lateral Area"), 10067.13, rel_tol=1e-3)
    assert math.isclose(_value(cone, "Volume"), 92700.57, rel_tol=1e-3)

    assert math.isclose(_value(portion, "Surface Area"), 11870.94, rel_tol=1e-3)
    assert math.isclose(_value(portion, "Volume"), 157148.86, rel_tol=1e-3)
    assert math.isclose(_value(portion, "Empty Volume"), 64448.29, rel_tol=1e-3)

    assert math.isclose(_value(frustum, "Surface Area"), 22384.98, rel_tol=1e-3)
    assert math.isclose(_value(frustum, "Volume"), 631952.20, rel_tol=1e-3)
    assert math.isclose(_value(frustum, "Capacity"), 15798.80, rel_tol=1e-3)

    assert math.isclose(_value(total, "Volume"), 789101.05, rel_tol=1e-3)
    assert math.isclose(_value(total, "Surface Area"), 34255.93, rel_tol=1e-3)


def test_dry_bulk_calculator_frustum_plus_cone_equals_product_volume():
    result = dry_bulk_storage_dome(
        diameter=80.0, height=40.0, stem_wall=20.0,
        angle_degrees=28.0, density=48.0, density_unit="lbs/ft3", length_unit="ft",
    )
    product = _section(result, "Product")
    cone = _section_starting_with(result, "Cone @")
    frustum = _section(result, "Frustum below cone")

    assert math.isclose(
        _value(product, "Volume"), _value(cone, "Volume") + _value(frustum, "Volume"), rel_tol=1e-9
    )


def test_dry_bulk_sizer_reference_example_from_monolithic_dome_institute():
    # angle=32, density=50 lbs/ft3, capacity=10000 ton, 16 ft stem wall --
    # cross-checked against the published Dry Bulk Storage Dome Sizer's
    # "short" style example, which uses the same fixed 16 ft stem wall.
    result = dry_bulk_storage_sizer(
        capacity=10000.0, weight_unit="ton", density=50.0, density_unit="lbs/ft3",
        angle_degrees=32.0, stem_wall=16.0, length_unit="ft",
    )
    product = _section(result, "Product")
    floor = _section_starting_with(result, "Floor:")
    dome = _section_starting_with(result, "Dome:")
    stem_wall = _section_starting_with(result, "Stem Wall:")
    total = _section_starting_with(result, "Total:")

    assert math.isclose(_value(product, "Capacity"), 10000.0, rel_tol=1e-6)
    assert math.isclose(_value(floor, "Radius"), 52.81, rel_tol=1e-3)
    assert math.isclose(_value(dome, "Radius of Curvature"), 52.81, rel_tol=1e-3)
    assert math.isclose(_value(stem_wall, "Volume"), 140184.72, rel_tol=1e-3)
    assert math.isclose(_value(total, "Volume"), 448648.97, rel_tol=1e-3)


def test_dry_bulk_sizer_solved_dome_reproduces_target_capacity_in_calculator():
    # Whatever the Sizer solves for should, fed back into the Calculator,
    # reproduce the same capacity -- a consistency check between the two.
    stem_wall = 25.0
    sizer_result = dry_bulk_storage_sizer(
        capacity=5000.0, weight_unit="ton", density=60.0, density_unit="lbs/ft3",
        angle_degrees=30.0, stem_wall=stem_wall, length_unit="ft",
    )
    floor = _section_starting_with(sizer_result, "Floor:")
    dome = _section_starting_with(sizer_result, "Dome:")

    diameter = 2 * _value(floor, "Radius")
    height = _value(dome, "Radius of Curvature")  # hemisphere: height == radius

    calculator_result = dry_bulk_storage_dome(
        diameter=diameter, height=height, stem_wall=stem_wall,
        angle_degrees=30.0, density=60.0, density_unit="lbs/ft3", length_unit="ft",
    )
    assert math.isclose(
        _value(_section(calculator_result, "Product"), "Capacity"), 5000.0, rel_tol=1e-3
    )


def test_dry_bulk_calculator_freeboard_zero_matches_no_freeboard_default():
    with_default = dry_bulk_storage_dome(
        diameter=116.0, height=58.0, stem_wall=36.0,
        angle_degrees=32.0, density=50.0, density_unit="lbs/ft3", length_unit="ft",
    )
    with_explicit_zero = dry_bulk_storage_dome(
        diameter=116.0, height=58.0, stem_wall=36.0,
        angle_degrees=32.0, density=50.0, density_unit="lbs/ft3", length_unit="ft", freeboard=0.0,
    )
    assert math.isclose(
        _value(_section(with_default, "Product"), "Volume"),
        _value(_section(with_explicit_zero, "Product"), "Volume"),
        rel_tol=1e-9,
    )


def test_dry_bulk_calculator_freeboard_strictly_reduces_capacity():
    kwargs = dict(diameter=116.0, height=58.0, stem_wall=36.0, angle_degrees=32.0, density=50.0, density_unit="lbs/ft3", length_unit="ft")
    no_freeboard = dry_bulk_storage_dome(**kwargs, freeboard=0.0)
    with_freeboard = dry_bulk_storage_dome(**kwargs, freeboard=20.0)

    no_freeboard_volume = _value(_section(no_freeboard, "Product"), "Volume")
    with_freeboard_volume = _value(_section(with_freeboard, "Product"), "Volume")
    assert with_freeboard_volume < no_freeboard_volume

    # The pile's peak should now sit exactly `freeboard` below the true apex.
    cone = _section_starting_with(with_freeboard, "Cone @")
    assert math.isclose(_value(cone, "Peak Height Above Floor"), 94.0 - 20.0, rel_tol=1e-9)


def test_dry_bulk_calculator_too_much_freeboard_raises_helpful_error():
    with pytest.raises(ValueError):
        dry_bulk_storage_dome(
            diameter=116.0, height=58.0, stem_wall=36.0,
            angle_degrees=32.0, density=50.0, density_unit="lbs/ft3", length_unit="ft", freeboard=94.0,
        )


def test_dry_bulk_sizer_accepts_freeboard_and_still_hits_target_capacity():
    result = dry_bulk_storage_sizer(
        capacity=10000.0, weight_unit="ton", density=50.0, density_unit="lbs/ft3",
        angle_degrees=32.0, stem_wall=16.0, length_unit="ft", freeboard=5.0,
    )
    assert math.isclose(_value(_section(result, "Product"), "Capacity"), 10000.0, rel_tol=1e-3)


def test_dry_bulk_calculator_t_per_m3_density_unit():
    # 1 t/m3 == 1000 kg/m3, so this should match a kg/m3 call scaled by 1000.
    in_t = dry_bulk_storage_dome(
        diameter=30.0, height=15.0, stem_wall=5.0,
        angle_degrees=30.0, density=1.6, density_unit="t/m3", length_unit="m",
    )
    in_kg = dry_bulk_storage_dome(
        diameter=30.0, height=15.0, stem_wall=5.0,
        angle_degrees=30.0, density=1600.0, density_unit="kg/m3", length_unit="m",
    )
    assert math.isclose(
        _value(_section(in_t, "Product"), "Capacity"),
        _value(_section(in_kg, "Product"), "Capacity"),
        rel_tol=1e-9,
    )


def test_live_dead_reclaim_reproduces_pa0004_document():
    # South Industries PA0004 Option A: 20.12 m dia hemisphere on a 17.98 m
    # stem wall, 37 deg repose, 70 deg drawdown, 0.61 m freeboard, single
    # centered 1.524 m (5 ft) square hopper. Doc: total 7,105.2 m3, live
    # 2,313 m3, dead 4,792 m3 (32.6% live), channel meets surface at 8.43 m.
    from geometry import live_dead_reclaim

    reclaim = live_dead_reclaim(
        diameter=20.12, dome_height=10.06, stem_wall=17.98,
        repose_deg=37.0, drawdown_deg=70.0, freeboard=0.61,
        openings=[(0.0, 0.0, 1.524, 1.524)],
    )
    assert math.isclose(reclaim["core"]["product_volume"], 7105.2, rel_tol=5e-3)
    assert math.isclose(reclaim["live_volume"], 2313.0, rel_tol=1.5e-2)
    assert math.isclose(reclaim["dead_volume"], 4792.0, rel_tol=1.5e-2)
    assert math.isclose(reclaim["live_share"], 0.326, rel_tol=2e-2)
    assert math.isclose(reclaim["channel_reach"], 8.43, rel_tol=1e-2)


def test_live_dead_larger_and_longer_openings_recover_more():
    from geometry import live_dead_reclaim

    kwargs = dict(
        diameter=20.12, dome_height=10.06, stem_wall=17.98,
        repose_deg=37.0, drawdown_deg=70.0, freeboard=0.61, samples=160,
    )
    base = live_dead_reclaim(openings=[(0.0, 0.0, 1.524, 1.524)], **kwargs)["live_volume"]
    bigger = live_dead_reclaim(openings=[(0.0, 0.0, 1.83, 1.83)], **kwargs)["live_volume"]
    longer = live_dead_reclaim(openings=[(0.0, 0.0, 1.83, 6.1)], **kwargs)["live_volume"]
    assert base < bigger < longer


def test_live_dead_multiple_openings_union_beats_single():
    from geometry import live_dead_reclaim

    kwargs = dict(
        diameter=20.12, dome_height=10.06, stem_wall=17.98,
        repose_deg=37.0, drawdown_deg=70.0, freeboard=0.61, samples=160,
    )
    single = live_dead_reclaim(openings=[(0.0, 0.0, 1.524, 1.524)], **kwargs)
    # Symmetric pair of inline hoppers 8 m apart (as along a reclaim tunnel).
    pair = live_dead_reclaim(
        openings=[(0.0, -4.0, 1.524, 1.524), (0.0, 4.0, 1.524, 1.524)], **kwargs
    )
    # Two channels overlap mid-span and the off-center ones sit under a lower
    # product surface, so the union lands well between 1x and 2x a single.
    assert single["live_volume"] * 1.3 < pair["live_volume"] < single["live_volume"] * 2.0
    assert pair["dead_volume"] + pair["live_volume"] == pytest.approx(
        single["dead_volume"] + single["live_volume"]
    )


def test_live_dead_storage_sections_include_check_and_sensitivity():
    from geometry import live_dead_storage

    sections = live_dead_storage(
        diameter=66.0, dome_height=33.0, stem_wall=59.0, repose_deg=37.0,
        drawdown_deg=70.0, density=100.0, density_unit="lbs/ft3",
        length_unit="ft", freeboard=2.0, opening_width=5.0, opening_length=5.0,
        required_live=60.0,  # required live share, percent
    )
    titles = [title for title, _rows in sections]
    assert any(title.startswith("Reclaim") for title in titles)
    assert "Live Storage Check" in titles
    assert any(title.startswith("Opening Size Sensitivity") for title in titles)

    reclaim_rows = _section_starting_with(sections, "Reclaim")
    live = _value(reclaim_rows, "Live Volume")
    dead = _value(reclaim_rows, "Dead Volume")
    product = _value(_section(sections, "Product"), "Volume")
    assert live + dead == pytest.approx(product)
