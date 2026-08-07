import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geometry import spherical_dome


def test_hemisphere_matches_known_formulas():
    diameter = 100.0
    radius = diameter / 2
    result = spherical_dome(diameter=diameter, height=radius, stem_wall=0)

    assert math.isclose(result["radius"], radius)
    assert math.isclose(result["radius_of_curvature"], radius, rel_tol=1e-9)
    assert math.isclose(result["dome_surface_area"], 2 * math.pi * radius ** 2, rel_tol=1e-9)
    assert math.isclose(result["dome_volume"], (2 / 3) * math.pi * radius ** 3, rel_tol=1e-9)


def test_stem_wall_adds_cylinder_volume():
    diameter = 100.0
    radius = diameter / 2
    stem_wall = 10.0
    result = spherical_dome(diameter=diameter, height=radius, stem_wall=stem_wall)

    cylinder_volume = math.pi * radius ** 2 * stem_wall
    dome_only = spherical_dome(diameter=diameter, height=radius, stem_wall=0)

    assert math.isclose(result["total_volume"], dome_only["dome_volume"] + cylinder_volume, rel_tol=1e-9)
    assert math.isclose(result["total_height"], radius + stem_wall)


def test_reference_example_from_monolithic_dome_institute():
    # Cross-checked against the published Spherical Dome Calculator for
    # diameter=105, height=35 (values rounded to 2 decimals on their site).
    result = spherical_dome(diameter=105.0, height=35.0, stem_wall=0)

    assert math.isclose(result["circumference"], 329.87, rel_tol=1e-3)
    assert math.isclose(result["floor_area"], 8659.01, rel_tol=1e-3)
    assert math.isclose(result["radius_of_curvature"], 56.88, rel_tol=1e-3)
