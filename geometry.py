import math

# Each result row is (label, value, unit_power) where unit_power is how many
# times the unit is applied: 0 = dimensionless, 1 = unit, 2 = unit^2, 3 = unit^3.

# All ellipsoid shapes are modeled as a "zone" of a spheroid of revolution:
# x^2/a^2 + z^2/b^2 = 1, cut horizontally between z1 and z2 (z measured from
# the ellipsoid's center, apex at z = b). A half-ellipsoid dome is just the
# special case z1 = 0, z2 = b.


def _ellipsoid_radius_at(a, b, z):
    return a * math.sqrt(1 - (z / b) ** 2)


def _ellipsoid_zone_arc_length(a, b, theta1, theta2, num_segments=2000):
    """Meridian arc length between two angles via Simpson's rule.

    theta is measured so that x = a*cos(theta), z = b*sin(theta) (theta = pi/2
    at the apex). No elementary closed form exists for this integral, so it's
    evaluated numerically instead of adding a scipy dependency; num_segments
    is far more than needed for 2-decimal calculator precision.
    """
    if num_segments % 2:
        num_segments += 1
    step = (theta2 - theta1) / num_segments

    def integrand(t):
        return math.hypot(a * math.sin(t), b * math.cos(t))

    total = integrand(theta1) + integrand(theta2)
    for i in range(1, num_segments):
        weight = 4 if i % 2 else 2
        total += weight * integrand(theta1 + i * step)
    return total * step / 3


def _ellipsoid_zone_surface_area(a, b, z1, z2):
    """Closed-form lateral surface area of a spheroid zone between z1 and z2."""
    if math.isclose(a, b, rel_tol=1e-9):
        return 2 * math.pi * a * (z2 - z1)  # sphere: Archimedes' zone formula

    c = b ** 4
    k = a ** 2 - b ** 2

    def antiderivative(z):
        if k > 0:  # oblate: equatorial radius a is the larger axis
            sk = math.sqrt(k)
            return (z / 2) * math.sqrt(c + k * z ** 2) + (c / (2 * sk)) * math.asinh(z * sk / math.sqrt(c))
        m = -k  # prolate: vertical radius b is the larger axis
        sm = math.sqrt(m)
        return (z / 2) * math.sqrt(c - m * z ** 2) + (c / (2 * sm)) * math.asin(z * sm / math.sqrt(c))

    return (2 * math.pi * a / b ** 2) * (antiderivative(z2) - antiderivative(z1))


def _ellipsoid_zone_volume(a, b, z1, z2):
    def antiderivative(z):
        return math.pi * a ** 2 * (z - z ** 3 / (3 * b ** 2))

    return antiderivative(z2) - antiderivative(z1)


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
    semi-axis (b) of the ellipsoid. The base always sits at the equator (z=0).
    """
    a = diameter / 2
    b = height

    circumference = 2 * math.pi * a
    floor_area = math.pi * a ** 2

    ellipticity_ratio = a / b
    curvature = a ** 2 / b
    theta_floor = 0.0  # base is at the equator
    surface_distance = _ellipsoid_zone_arc_length(a, b, theta_floor, math.pi / 2)
    dome_surface_area = _ellipsoid_zone_surface_area(a, b, 0.0, b)
    dome_volume = _ellipsoid_zone_volume(a, b, 0.0, b)

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


def vertical_ellipsoid_dome(horizontal, vertical, height):
    """Geometry for a vertical ellipsoid dome: circular base, elliptical cross-section.

    `horizontal` (a) and `vertical` (b) define the full ellipsoid's semi-axes.
    `height` is measured from the floor to the apex, and may be more or less
    than `vertical` -- the floor can sit above or below the equator. No stem
    wall: the floor position within the ellipsoid does that job instead.
    """
    a, b = horizontal, vertical
    z_apex = b
    z_floor = b - height

    floor_radius = _ellipsoid_radius_at(a, b, z_floor)
    circumference = 2 * math.pi * floor_radius
    floor_area = math.pi * floor_radius ** 2

    ellipticity_ratio = a / b
    curvature = a ** 2 / b
    theta_floor = math.asin(z_floor / b)
    surface_distance = _ellipsoid_zone_arc_length(a, b, theta_floor, math.pi / 2)
    dome_surface_area = _ellipsoid_zone_surface_area(a, b, z_floor, z_apex)
    dome_volume = _ellipsoid_zone_volume(a, b, z_floor, z_apex)

    return {
        "floor": [
            ("Radius", floor_radius, 1),
            ("Circumference", circumference, 1),
            ("Area", floor_area, 2),
        ],
        "dome": [
            ("Horizontal Radius", a, 1),
            ("Vertical Radius", b, 1),
            ("Ellipticity Ratio", ellipticity_ratio, 0),
            ("Curvature", curvature, 1),
            ("Surface Distance", surface_distance, 1),
            ("Surface Area", dome_surface_area, 2),
            ("Volume", dome_volume, 3),
            ("Overall Height", height, 1),
        ],
    }
