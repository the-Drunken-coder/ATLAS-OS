"""Tests for geo.destination_point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geo import destination_point


def test_zero_distance():
    lat, lon = destination_point(34.0, -118.0, 90.0, 0.0)
    assert abs(lat - 34.0) < 1e-9
    assert abs(lon - (-118.0)) < 1e-9


def test_north():
    lat, lon = destination_point(34.0, -118.0, 0.0, 1000.0)
    assert lat > 34.0
    assert abs(lon - (-118.0)) < 1e-6


def test_east():
    lat, lon = destination_point(34.0, -118.0, 90.0, 1000.0)
    assert abs(lat - 34.0) < 1e-4
    assert lon > -118.0


def test_south():
    lat, lon = destination_point(34.0, -118.0, 180.0, 1000.0)
    assert lat < 34.0


def test_40_feet():
    lat, lon = destination_point(34.0522, -118.2437, 45.0, 12.192)
    assert abs(lat - 34.0522) < 0.001
    assert abs(lon - (-118.2437)) < 0.001
    assert not (lat == 34.0522 and lon == -118.2437)


def test_one_degree_north():
    lat, _ = destination_point(0.0, 0.0, 0.0, 111_320.0)
    assert abs(lat - 1.0) < 0.01


def test_round_trip():
    mid_lat, mid_lon = destination_point(34.0, -118.0, 0.0, 5000.0)
    back_lat, back_lon = destination_point(mid_lat, mid_lon, 180.0, 5000.0)
    assert abs(back_lat - 34.0) < 1e-6
    assert abs(back_lon - (-118.0)) < 1e-6
