import pytest
from modules.operations.geo import haversine_meters


def test_haversine_same_point():
    """Test that distance between same point is zero."""
    distance = haversine_meters(0.0, 0.0, 0.0, 0.0)
    assert distance == 0.0


def test_haversine_known_distances():
    """Test haversine calculation with known distances."""
    # New York to London (roughly 5570 km)
    # NY: 40.7128° N, 74.0060° W
    # London: 51.5074° N, 0.1278° W
    distance = haversine_meters(40.7128, -74.0060, 51.5074, -0.1278)
    # Allow 1% tolerance
    assert 5500000 < distance < 5600000
    
    # Equator: 1 degree of longitude at equator is approximately 111.32 km
    distance = haversine_meters(0.0, 0.0, 0.0, 1.0)
    assert 111000 < distance < 112000
    
    # Short distance: approximately 100m
    # Using small differences at mid-latitudes
    distance = haversine_meters(40.0, -74.0, 40.001, -74.0)
    assert 100 < distance < 120


def test_haversine_equator():
    """Test haversine calculation along the equator."""
    # 1 degree longitude at equator ≈ 111.32 km
    distance = haversine_meters(0.0, 0.0, 0.0, 1.0)
    assert 111000 < distance < 112000
    
    # 10 degrees longitude
    distance = haversine_meters(0.0, 0.0, 0.0, 10.0)
    assert 1110000 < distance < 1115000


def test_haversine_poles():
    """Test haversine calculation near poles."""
    # North pole to slightly offset (0.1 degree south)
    distance = haversine_meters(89.9, 0.0, 90.0, 0.0)
    assert distance > 0
    assert distance < 20000  # Should be relatively small
    
    # At very high latitudes, longitude differences still create distance
    # but it's smaller than at the equator
    dist_poles = haversine_meters(89.0, 0.0, 89.0, 180.0)
    dist_equator = haversine_meters(0.0, 0.0, 0.0, 180.0)
    # Distance at poles should be less than at equator
    assert dist_poles < dist_equator


def test_haversine_antipodal_points():
    """Test haversine with points on opposite sides of Earth."""
    # Points on opposite sides should be roughly 20,000 km apart (half Earth's circumference)
    distance = haversine_meters(0.0, 0.0, 0.0, 180.0)
    # Half of Earth's circumference at equator
    assert 19900000 < distance < 20100000


def test_haversine_negative_coordinates():
    """Test haversine with negative (southern/western) coordinates."""
    # Southern hemisphere
    distance = haversine_meters(-33.8688, 151.2093, -34.0, 151.0)  # Sydney area
    assert distance > 0
    assert distance < 50000
    
    # Western hemisphere
    distance = haversine_meters(40.7128, -74.0060, 40.7589, -73.9851)  # NYC area
    assert distance > 0
    assert distance < 10000


def test_haversine_ordering_doesnt_matter():
    """Test that point order doesn't affect distance."""
    dist1 = haversine_meters(40.7128, -74.0060, 51.5074, -0.1278)
    dist2 = haversine_meters(51.5074, -0.1278, 40.7128, -74.0060)
    assert abs(dist1 - dist2) < 0.001  # Should be essentially identical


def test_haversine_small_distances():
    """Test haversine accuracy for small distances."""
    # Very small distance (approximately 10 meters)
    distance = haversine_meters(40.0, -74.0, 40.00009, -74.0)
    assert 9 < distance < 11
    
    # Approximately 25 meters
    distance = haversine_meters(40.0, -74.0, 40.000225, -74.0)
    assert 24 < distance < 26


def test_haversine_various_coordinate_ranges():
    """Test haversine with various valid coordinate ranges."""
    # Valid latitude range: -90 to 90
    # Valid longitude range: -180 to 180
    
    # Extreme north
    distance = haversine_meters(89.0, 0.0, 90.0, 0.0)
    assert distance > 0
    
    # Extreme south
    distance = haversine_meters(-89.0, 0.0, -90.0, 0.0)
    assert distance > 0
    
    # Crossing date line
    distance = haversine_meters(0.0, 179.0, 0.0, -179.0)
    # Should be approximately 222 km (2 degrees at equator)
    assert 220000 < distance < 225000
