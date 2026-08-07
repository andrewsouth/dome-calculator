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


def _circular_segment_area(radius, chord_height):
    """Area of the part of a circle (centered at origin) above z = chord_height."""
    if radius <= 1e-12:
        return 0.0
    if chord_height <= -radius:
        return math.pi * radius ** 2
    if chord_height >= radius:
        return 0.0
    return radius ** 2 * math.acos(chord_height / radius) - chord_height * math.sqrt(
        max(radius ** 2 - chord_height ** 2, 0.0)
    )


def _horizontal_ellipsoid_zone(major, minor, z_floor, num_segments=5000):
    """Volume and lateral surface area of a horizontal ellipsoid dome.

    The ellipsoid (x/major)^2 + (y/minor)^2 + (z/minor)^2 = 1 lies on its
    side (revolution axis "major" is horizontal), cut by the horizontal
    floor plane z = z_floor. Because the cut is parallel to the axis of
    revolution rather than perpendicular to it, each cross-section along x
    is a circular *segment* rather than a full circle or ellipse, and there
    is no elementary closed form -- so, like the reference calculator itself
    (which iterates over 72,000 segments), this integrates numerically along
    the major axis using exact per-slice circle geometry.
    """
    a, b = major, minor

    def radius_at(x):
        value = 1 - (x / a) ** 2
        return b * math.sqrt(value) if value > 1e-15 else 0.0

    def radius_slope_at(x):
        value = 1 - (x / a) ** 2
        if value <= 1e-15:
            return 0.0
        return -b * x / (a ** 2 * math.sqrt(value))

    def volume_integrand(x):
        return _circular_segment_area(radius_at(x), z_floor)

    def surface_integrand(x):
        radius = radius_at(x)
        if radius <= 1e-9:
            return 0.0
        if z_floor <= -radius:
            arc_angle = 2 * math.pi
        elif z_floor >= radius:
            return 0.0
        else:
            arc_angle = 2 * math.acos(z_floor / radius)
        return radius * arc_angle * math.hypot(1, radius_slope_at(x))

    if num_segments % 2:
        num_segments += 1
    edge_offset = 1e-7  # radius_at(+-a) is exactly 0; nudge inside the domain
    step = (2 * a - 2 * edge_offset) / num_segments
    start = -a + edge_offset

    def integrate(f):
        total = f(start) + f(start + num_segments * step)
        for i in range(1, num_segments):
            weight = 4 if i % 2 else 2
            total += weight * f(start + i * step)
        return total * step / 3

    return integrate(volume_integrand), integrate(surface_integrand)


def horizontal_ellipsoid_dome(major, minor, height):
    """Geometry for a horizontal ellipsoid dome: elliptical floor, lying on its side.

    `major` (a) is the horizontal semi-axis along the ellipsoid's axis of
    revolution; `minor` (b) is shared by the other two (vertical and the
    other horizontal) axes. `height` is measured from the floor to the apex.
    """
    a, b = major, minor
    z_floor = b - height

    scale = math.sqrt(1 - (z_floor / b) ** 2)
    floor_major = a * scale
    floor_minor = b * scale
    floor_area = math.pi * floor_major * floor_minor
    floor_perimeter = 4 * _ellipsoid_zone_arc_length(floor_major, floor_minor, 0.0, math.pi / 2)
    foci = math.sqrt(abs(floor_major ** 2 - floor_minor ** 2))

    ellipticity_ratio = b / a
    theta_floor = math.asin(z_floor / b)
    surface_distance = _ellipsoid_zone_arc_length(a, b, theta_floor, math.pi / 2)
    dome_volume, dome_surface_area = _horizontal_ellipsoid_zone(a, b, z_floor)

    return {
        "floor": [
            ("Major Diameter", 2 * floor_major, 1),
            ("Minor Diameter", 2 * floor_minor, 1),
            ("Perimeter", floor_perimeter, 1),
            ("Area", floor_area, 2),
            ("Foci (±)", foci, 1),
        ],
        "dome": [
            ("Major Radius", a, 1),
            ("Minor Radius", b, 1),
            ("Overall Height", height, 1),
            ("Ellipticity Ratio", ellipticity_ratio, 0),
            ("Surface Distance", surface_distance, 1),
            ("Surface Area", dome_surface_area, 2),
            ("Volume", dome_volume, 3),
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
