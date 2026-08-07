import math


def spherical_dome(diameter, height, stem_wall=0.0):
    """Compute geometry for a spherical-cap dome on an optional cylindrical stem wall.

    diameter, height, stem_wall are all in the same unit; height is the dome
    cap height only (not including the stem wall).
    """
    radius = diameter / 2

    circumference = 2 * math.pi * radius
    floor_area = math.pi * radius ** 2

    # Sphere radius that produces a cap of this base radius and height.
    radius_of_curvature = (radius ** 2 + height ** 2) / (2 * height)

    # Angle from the sphere's center subtended by the cap, used for arc length.
    cap_angle = math.acos((radius_of_curvature - height) / radius_of_curvature)
    surface_distance = radius_of_curvature * cap_angle

    dome_surface_area = 2 * math.pi * radius_of_curvature * height
    dome_volume = (math.pi * height ** 2 / 3) * (3 * radius_of_curvature - height)

    stem_wall_surface_area = 2 * math.pi * radius * stem_wall
    stem_wall_volume = math.pi * radius ** 2 * stem_wall

    return {
        "radius": radius,
        "circumference": circumference,
        "floor_area": floor_area,
        "radius_of_curvature": radius_of_curvature,
        "surface_distance": surface_distance,
        "dome_surface_area": dome_surface_area,
        "dome_volume": dome_volume,
        "stem_wall_surface_area": stem_wall_surface_area,
        "stem_wall_volume": stem_wall_volume,
        "total_surface_area": dome_surface_area + stem_wall_surface_area,
        "total_volume": dome_volume + stem_wall_volume,
        "total_height": height + stem_wall,
    }
