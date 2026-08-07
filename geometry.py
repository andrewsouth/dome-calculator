import math

# Each result row is (label, value, unit_power) where unit_power is how many
# times the unit is applied: 0 = dimensionless, 1 = unit, 2 = unit^2, 3 = unit^3.


def _quarter_meridian_arc_length(p, q, num_segments=2000):
    """Arc length of a quarter ellipse (semi-axes p, q) via Simpson's rule.

    Used instead of scipy's elliptic integrals to keep the project
    dependency-free; num_segments is far more than needed for 2-decimal
    calculator precision.
    """
    if num_segments % 2:
        num_segments += 1
    step = (math.pi / 2) / num_segments

    def integrand(t):
        return math.hypot(p * math.sin(t), q * math.cos(t))

    total = integrand(0) + integrand(math.pi / 2)
    for i in range(1, num_segments):
        weight = 4 if i % 2 else 2
        total += weight * integrand(i * step)
    return total * step / 3


def _half_ellipsoid_surface_area(a, b):
    """Curved surface area of a half ellipsoid of revolution (no base cap)."""
    if math.isclose(a, b, rel_tol=1e-9):
        return 2 * math.pi * a ** 2  # hemisphere

    if a > b:  # oblate: flattened, equatorial radius a is the larger axis
        e = math.sqrt(1 - (b / a) ** 2)
        full = 2 * math.pi * a ** 2 + (math.pi * b ** 2 / e) * math.log((1 + e) / (1 - e))
    else:  # prolate: stretched, height b is the larger axis
        e = math.sqrt(1 - (a / b) ** 2)
        full = 2 * math.pi * a ** 2 + (2 * math.pi * a * b / e) * math.asin(e)
    return full / 2


def spherical_dome(diameter, height, stem_wall=0.0):
    """Geometry for a spherical-cap dome on an optional cylindrical stem wall."""
    radius = diameter / 2

    circumference = 2 * math.pi * radius
    floor_area = math.pi * radius ** 2

    radius_of_curvature = (radius ** 2 + height ** 2) / (2 * height)
    cap_angle = math.acos((radius_of_curvature - height) / radius_of_curvature)
    surface_distance = radius_of_curvature * cap_angle

    dome_surface_area = 2 * math.pi * radius_of_curvature * height
    dome_volume = (math.pi * height ** 2 / 3) * (3 * radius_of_curvature - height)

    stem_wall_surface_area = 2 * math.pi * radius * stem_wall
    stem_wall_volume = math.pi * radius ** 2 * stem_wall

    return {
        "floor": [
            ("Radius", radius, 1),
            ("Circumference", circumference, 1),
            ("Area", floor_area, 2),
        ],
        "dome": [
            ("Radius of Curvature", radius_of_curvature, 1),
            ("Surface Distance", surface_distance, 1),
            ("Surface Area", dome_surface_area + stem_wall_surface_area, 2),
            ("Volume", dome_volume + stem_wall_volume, 3),
            ("Total Height", height + stem_wall, 1),
        ],
    }


def ellipsoid_dome(diameter, height, stem_wall=0.0):
    """Geometry for a half-ellipsoid dome (oblate or prolate) on an optional stem wall.

    `diameter` sets the equatorial radius (a); `height` is the vertical
    semi-axis (b) of the ellipsoid.
    """
    a = diameter / 2
    b = height

    circumference = 2 * math.pi * a
    floor_area = math.pi * a ** 2

    ellipticity_ratio = a / b
    curvature = a ** 2 / b
    surface_distance = _quarter_meridian_arc_length(max(a, b), min(a, b))
    dome_surface_area = _half_ellipsoid_surface_area(a, b)
    dome_volume = (2 / 3) * math.pi * a ** 2 * b

    stem_wall_surface_area = 2 * math.pi * a * stem_wall
    stem_wall_volume = math.pi * a ** 2 * stem_wall

    return {
        "floor": [
            ("Radius", a, 1),
            ("Circumference", circumference, 1),
            ("Area", floor_area, 2),
        ],
        "dome": [
            ("Ellipticity Ratio", ellipticity_ratio, 0),
            ("Curvature", curvature, 1),
            ("Surface Distance", surface_distance, 1),
            ("Surface Area", dome_surface_area + stem_wall_surface_area, 2),
            ("Volume", dome_volume + stem_wall_volume, 3),
            ("Total Height", height + stem_wall, 1),
        ],
    }
