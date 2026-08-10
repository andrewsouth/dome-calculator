import math

# Each result row is (label, value, unit_suffix). unit_suffix is either an int
# -- how many times the shape's chosen length unit is applied (0 = dimensionless,
# 1 = unit, 2 = unit^2, 3 = unit^3) -- or a literal string shown as-is (e.g.
# "°", "ton", "lbs/ft³") for values that aren't in the length unit.

LB_TO_KG = 0.45359237
FT3_TO_M3 = 0.028316846592
BU_TO_FT3 = 1.2444560268
US_TON_TO_KG = 2000 * LB_TO_KG
LB_PER_FT3_TO_KG_PER_M3 = LB_TO_KG / FT3_TO_M3

# All ellipsoid shapes are modeled as a "zone" of a spheroid of revolution:
# x^2/a^2 + z^2/b^2 = 1, cut horizontally between z1 and z2 (z measured from
# the ellipsoid's center, apex at z = b). A half-ellipsoid dome is just the
# special case z1 = 0, z2 = b.


def _ellipsoid_radius_at(a, b, z):
    return a * math.sqrt(1 - (z / b) ** 2)


def _safe_asin(x):
    """asin with the argument clamped to [-1, 1], guarding against float
    overshoot when x is mathematically exactly +-1 (e.g. a hemisphere's apex)."""
    return math.asin(max(-1.0, min(1.0, x)))


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

    return [
        ("Floor", [
            ("Radius", radius, 1),
            ("Circumference", circumference, 1),
            ("Area", floor_area, 2),
        ]),
        ("Dome", [
            ("Radius of Curvature", radius_of_curvature, 1),
            ("Surface Distance", surface_distance, 1),
            ("Surface Area", dome_surface_area + stem_wall_surface_area, 2),
            ("Volume", dome_volume + stem_wall_volume, 3),
            ("Total Height", height + stem_wall, 1),
        ]),
    ]


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

    return [
        ("Floor", [
            ("Radius", a, 1),
            ("Circumference", circumference, 1),
            ("Area", floor_area, 2),
        ]),
        ("Dome", [
            ("Ellipticity Ratio", ellipticity_ratio, 0),
            ("Curvature", curvature, 1),
            ("Surface Distance", surface_distance, 1),
            ("Surface Area", dome_surface_area + stem_wall_surface_area, 2),
            ("Volume", dome_volume + stem_wall_volume, 3),
            ("Total Height", height + stem_wall, 1),
        ]),
    ]


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

    return [
        ("Floor Ellipse", [
            ("Major Diameter", 2 * floor_major, 1),
            ("Minor Diameter", 2 * floor_minor, 1),
            ("Perimeter", floor_perimeter, 1),
            ("Area", floor_area, 2),
            ("Foci (±)", foci, 1),
        ]),
        ("Dome", [
            ("Major Radius", a, 1),
            ("Minor Radius", b, 1),
            ("Overall Height", height, 1),
            ("Ellipticity Ratio", ellipticity_ratio, 0),
            ("Surface Distance", surface_distance, 1),
            ("Surface Area", dome_surface_area, 2),
            ("Volume", dome_volume, 3),
        ]),
    ]


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

    return [
        ("Floor", [
            ("Radius", floor_radius, 1),
            ("Circumference", circumference, 1),
            ("Area", floor_area, 2),
        ]),
        ("Dome", [
            ("Horizontal Radius", a, 1),
            ("Vertical Radius", b, 1),
            ("Ellipticity Ratio", ellipticity_ratio, 0),
            ("Curvature", curvature, 1),
            ("Surface Distance", surface_distance, 1),
            ("Surface Area", dome_surface_area, 2),
            ("Volume", dome_volume, 3),
            ("Overall Height", height, 1),
        ]),
    ]


def ellipse(major, minor):
    """Geometry for a plain 2D ellipse (not a dome -- e.g. a floor plan shape)."""
    a, b = major, minor

    circumference = 4 * _ellipsoid_zone_arc_length(a, b, 0.0, math.pi / 2)
    area = math.pi * a * b
    curvature = a ** 2 / b
    foci = math.sqrt(abs(a ** 2 - b ** 2))

    return [
        ("Ellipse", [
            ("Major Radius", a, 1),
            ("Minor Radius", b, 1),
            ("Circumference", circumference, 1),
            ("Curvature", curvature, 1),
            ("Area", area, 2),
            ("Foci (±)", foci, 1),
        ]),
    ]


# -- Dry Bulk Storage: material poured into a dome piles up at its angle of
# repose. Below the point where the pile's slope meets the structure wall,
# material completely fills the interior (stem wall + lower dome, no gaps).
# Above that point, the material forms a freestanding cone that doesn't touch
# the curved dome ceiling, leaving an air gap ("empty volume").


def _cone_geometry(radius, height):
    slant = math.hypot(radius, height)
    lateral_area = math.pi * radius * slant
    volume = (math.pi / 3) * radius ** 2 * height
    return slant, lateral_area, volume


def _dry_bulk_cone_transition(radius_of_curvature, floor_radius, dome_height, stem_wall, angle):
    """Where the pile's angle-of-repose line from the apex meets the structure.

    Returns (cone_radius, height_above_floor). The line from the apex, sloped
    at `angle` from horizontal, generically meets the spherical dome curve
    again at radius = radius_of_curvature * sin(2*angle) (derived by
    substituting the line z = H - r*tan(angle) into the sphere equation). If
    that radius would exceed the floor radius, the line reaches the vertical
    stem wall first instead.
    """
    r_cone = radius_of_curvature * math.sin(2 * angle)
    if r_cone <= floor_radius:
        height_above_dome_base = dome_height - r_cone * math.tan(angle)
        return r_cone, stem_wall + height_above_dome_base

    height_above_dome_base = dome_height - floor_radius * math.tan(angle)
    height_above_floor = stem_wall + height_above_dome_base
    if height_above_floor < 0:
        raise ValueError(
            "This angle of repose is too shallow for these dimensions -- "
            "the pile would need to extend below the floor. Try a taller "
            "structure or a steeper angle."
        )
    return floor_radius, height_above_floor


def _structure_zone(radius, radius_of_curvature, stem_wall, dome_height, h1, h2):
    """Volume and lateral surface area of the stem wall + dome between two
    heights above the floor (0 <= h1 <= h2 <= stem_wall + dome_height)."""
    volume = 0.0
    area = 0.0

    wall_lo, wall_hi = max(h1, 0.0), min(h2, stem_wall)
    if wall_hi > wall_lo:
        volume += math.pi * radius ** 2 * (wall_hi - wall_lo)
        area += 2 * math.pi * radius * (wall_hi - wall_lo)

    dome_lo, dome_hi = max(h1, stem_wall), min(h2, stem_wall + dome_height)
    if dome_hi > dome_lo:
        z1, z2 = dome_lo - stem_wall, dome_hi - stem_wall
        R = radius_of_curvature
        volume += _ellipsoid_zone_volume(R, R, z1, z2)
        area += _ellipsoid_zone_surface_area(R, R, z1, z2)

    return volume, area


def _structure_surface_distance(radius_of_curvature, stem_wall, dome_height, h1, h2):
    """Distance along the surface (up the stem wall, then along the dome curve)
    between two heights above the floor."""
    distance = 0.0

    wall_lo, wall_hi = max(h1, 0.0), min(h2, stem_wall)
    if wall_hi > wall_lo:
        distance += wall_hi - wall_lo

    dome_lo, dome_hi = max(h1, stem_wall), min(h2, stem_wall + dome_height)
    if dome_hi > dome_lo:
        R = radius_of_curvature
        theta1, theta2 = _safe_asin((dome_lo - stem_wall) / R), _safe_asin((dome_hi - stem_wall) / R)
        distance += _ellipsoid_zone_arc_length(R, R, theta1, theta2)

    return distance


def _dry_bulk_core(diameter, height, stem_wall, angle_degrees):
    """The raw numeric pieces shared by both the display function and the
    Sizer's root-finder (which only needs product_volume, repeatedly)."""
    radius = diameter / 2
    angle = math.radians(angle_degrees)
    radius_of_curvature = (radius ** 2 + height ** 2) / (2 * height)

    cone_radius, transition_height = _dry_bulk_cone_transition(
        radius_of_curvature, radius, height, stem_wall, angle
    )
    total_height = stem_wall + height
    cone_height = total_height - transition_height
    cone_slant, cone_lateral_area, cone_volume = _cone_geometry(cone_radius, cone_height)

    frustum_volume, frustum_area = _structure_zone(radius, radius_of_curvature, stem_wall, height, 0.0, transition_height)
    frustum_distance = _structure_surface_distance(radius_of_curvature, stem_wall, height, 0.0, transition_height)

    portion_volume, portion_area = _structure_zone(
        radius, radius_of_curvature, stem_wall, height, transition_height, total_height
    )
    portion_distance = _structure_surface_distance(radius_of_curvature, stem_wall, height, transition_height, total_height)

    return {
        "radius": radius,
        "radius_of_curvature": radius_of_curvature,
        "total_height": total_height,
        "cone_radius": cone_radius,
        "cone_height": cone_height,
        "cone_slant": cone_slant,
        "cone_lateral_area": cone_lateral_area,
        "cone_volume": cone_volume,
        "transition_height": transition_height,
        "frustum_volume": frustum_volume,
        "frustum_area": frustum_area,
        "frustum_distance": frustum_distance,
        "portion_volume": portion_volume,
        "portion_area": portion_area,
        "portion_distance": portion_distance,
        "empty_volume": portion_volume - cone_volume,
        "product_volume": frustum_volume + cone_volume,
    }


def _density_to_kg_per_m3(density, density_unit):
    return density * LB_PER_FT3_TO_KG_PER_M3 if density_unit == "lbs/ft3" else density


def _mass_kg(volume_native, length_unit, density, density_unit):
    volume_m3 = volume_native * FT3_TO_M3 if length_unit in ("ft", "in") else volume_native
    return volume_m3 * _density_to_kg_per_m3(density, density_unit)


def dry_bulk_storage_dome(diameter, height, stem_wall, angle_degrees, density, density_unit, length_unit):
    """Storage capacity of material (at a given angle of repose and density)
    poured into a spherical dome on an optional stem wall."""
    core = _dry_bulk_core(diameter, height, stem_wall, angle_degrees)
    radius, R = core["radius"], core["radius_of_curvature"]

    density_label = "lbs/ft³" if density_unit == "lbs/ft3" else "kg/m³"
    mass_unit_label = "ton" if length_unit in ("ft", "in") else "tonne"
    show_bushels = length_unit in ("ft", "in") and density_unit == "lbs/ft3"

    def capacity_row(volume_native):
        mass_kg = _mass_kg(volume_native, length_unit, density, density_unit)
        value = mass_kg / US_TON_TO_KG if mass_unit_label == "ton" else mass_kg / 1000.0
        return ("Capacity", value, mass_unit_label)

    product_rows = [
        ("Angle of Repose", angle_degrees, "°"),
        ("Density", density, density_label),
        ("Volume", core["product_volume"], 3),
        capacity_row(core["product_volume"]),
    ]
    if show_bushels:
        product_rows.append(("Bushels", core["product_volume"] / BU_TO_FT3, "bu"))

    cone_rows = [
        ("Above Floor", core["transition_height"], 1),
        ("Radius", core["cone_radius"], 1),
        ("Height", core["cone_height"], 1),
        ("Slant Length", core["cone_slant"], 1),
        ("Lateral Area", core["cone_lateral_area"], 2),
        ("Volume", core["cone_volume"], 3),
        capacity_row(core["cone_volume"]),
    ]

    portion_rows = [
        ("Remaining Height", core["total_height"] - core["transition_height"], 1),
        ("Surface Distance", core["portion_distance"], 1),
        ("Surface Area", core["portion_area"], 2),
        ("Volume", core["portion_volume"], 3),
        ("Empty Volume", core["empty_volume"], 3),
    ]

    frustum_rows = [
        ("Frustum Height", core["transition_height"], 1),
        ("Surface Distance", core["frustum_distance"], 1),
        ("Surface Area", core["frustum_area"], 2),
        ("Volume", core["frustum_volume"], 3),
        capacity_row(core["frustum_volume"]),
    ]

    floor_rows = [
        ("Radius", radius, 1),
        ("Circumference", 2 * math.pi * radius, 1),
        ("Area", math.pi * radius ** 2, 2),
    ]

    dome_volume = _ellipsoid_zone_volume(R, R, 0.0, height)
    dome_area = _ellipsoid_zone_surface_area(R, R, 0.0, height)
    dome_distance = _ellipsoid_zone_arc_length(R, R, 0.0, _safe_asin(height / R))
    dome_rows = [
        ("Radius of Curvature", R, 1),
        ("Surface Distance", dome_distance, 1),
        ("Surface Area", dome_area, 2),
        ("Volume", dome_volume, 3),
    ]

    stem_wall_area = 2 * math.pi * radius * stem_wall
    stem_wall_volume = math.pi * radius ** 2 * stem_wall
    stem_wall_rows = [
        ("Surface Area", stem_wall_area, 2),
        ("Volume", stem_wall_volume, 3),
    ]

    total_rows = [
        ("Surface Distance", dome_distance + stem_wall, 1),
        ("Surface Area", dome_area + stem_wall_area, 2),
        ("Volume", dome_volume + stem_wall_volume, 3),
    ]

    return [
        ("Product", product_rows),
        (f"Cone @ {core['transition_height']:.2f} {length_unit} above floor", cone_rows),
        ("Portion above cone", portion_rows),
        ("Frustum below cone", frustum_rows),
        (f"Floor: {diameter:.2f} {length_unit} diameter", floor_rows),
        (f"Dome: {height:.2f} {length_unit} height", dome_rows),
        (f"Stem Wall: {stem_wall:.2f} {length_unit} height", stem_wall_rows),
        (f"Total: {core['total_height']:.2f} {length_unit} height", total_rows),
    ]


def _dry_bulk_style_dimensions(style, radius, angle, short_stem_wall):
    if style == "hemi":
        return radius, 0.0
    if style == "short":
        return radius, short_stem_wall
    if style == "medium":
        return radius, radius / 2
    if style == "tall":
        return radius, radius
    if style == "pile":
        # Dome height chosen so the pile's repose line meets the dome curve
        # exactly at the floor edge -- no frustum, no stem wall, the dome
        # just clears the pile with no material touching it.
        return radius * math.tan(angle), 0.0
    raise ValueError(f"Unknown style: {style}")


def _dry_bulk_target_volume_native(capacity, weight_unit, density, density_unit, length_unit):
    if weight_unit == "bu":
        volume_m3 = capacity * BU_TO_FT3 * FT3_TO_M3
    else:
        mass_kg = {
            "lbs": capacity * LB_TO_KG,
            "ton": capacity * US_TON_TO_KG,
            "kg": capacity,
            "tonne": capacity * 1000.0,
        }[weight_unit]
        volume_m3 = mass_kg / _density_to_kg_per_m3(density, density_unit)
    return volume_m3 / FT3_TO_M3 if length_unit in ("ft", "in") else volume_m3


def dry_bulk_storage_sizer(capacity, weight_unit, density, density_unit, angle_degrees, style, length_unit):
    """Find the dome (of a given style) needed to store a target capacity.

    Reduces to a 1D root-find: for a fixed style, dome height and stem wall
    are both determined by a single "radius" parameter, so product_volume(radius)
    is a plain increasing function -- bisect on it, then hand the solved
    dimensions to dry_bulk_storage_dome for the actual display output.
    """
    angle = math.radians(angle_degrees)
    target_volume = _dry_bulk_target_volume_native(capacity, weight_unit, density, density_unit, length_unit)
    short_stem_wall = 5.0 if length_unit in ("m", "mm") else 16.0

    def product_volume_for(radius):
        height, stem_wall = _dry_bulk_style_dimensions(style, radius, angle, short_stem_wall)
        return _dry_bulk_core(2 * radius, height, stem_wall, angle_degrees)["product_volume"]

    low, high = 1e-3, 1.0
    for _ in range(200):
        if product_volume_for(high) >= target_volume:
            break
        high *= 2
    else:
        raise ValueError("Could not find a dome large enough for that capacity.")

    for _ in range(100):
        mid = (low + high) / 2
        if product_volume_for(mid) < target_volume:
            low = mid
        else:
            high = mid

    radius = (low + high) / 2
    height, stem_wall = _dry_bulk_style_dimensions(style, radius, angle, short_stem_wall)
    return dry_bulk_storage_dome(2 * radius, height, stem_wall, angle_degrees, density, density_unit, length_unit)
