"""Geodesic math — destination point calculation."""

import math

_EARTH_RADIUS_M = 6_371_008.8


def destination_point(lat, lon, bearing_deg, distance_m):
    """Return (lat, lon) of a point at *distance_m* along *bearing_deg* from start."""
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    br = math.radians(bearing_deg)
    d = distance_m / _EARTH_RADIUS_M

    lat2 = math.asin(
        math.sin(lat_r) * math.cos(d) + math.cos(lat_r) * math.sin(d) * math.cos(br)
    )
    lon2 = lon_r + math.atan2(
        math.sin(br) * math.sin(d) * math.cos(lat_r),
        math.cos(d) - math.sin(lat_r) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)
