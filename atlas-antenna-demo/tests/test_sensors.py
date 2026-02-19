"""Tests for GpsReader and AntennaReader (simulated mode)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gps import GpsReader
from antenna import AntennaReader


def test_gps_produces_position():
    gps = GpsReader({
        "simulated": True, "interval_s": 0.1,
        "sim_start_lat": 34.0, "sim_start_lon": -118.0,
        "sim_heading_deg": 0.0, "sim_speed_m_s": 1.0,
    })
    gps.start()
    time.sleep(0.4)
    gps.stop()

    pos = gps.get_position()
    assert pos is not None
    assert "latitude" in pos
    assert "longitude" in pos
    assert "heading_deg" in pos
    assert "altitude_m" not in pos
    assert "speed_m_s" not in pos


def test_gps_position_advances_north():
    gps = GpsReader({
        "simulated": True, "interval_s": 0.1,
        "sim_start_lat": 34.0, "sim_start_lon": -118.0,
        "sim_heading_deg": 0.0, "sim_speed_m_s": 10.0,
    })
    gps.start()
    time.sleep(0.15)
    first = gps.get_position()
    time.sleep(0.4)
    last = gps.get_position()
    gps.stop()

    assert first is not None and last is not None
    assert last["latitude"] > first["latitude"]


def test_antenna_sim_returns_dbm():
    ant = AntennaReader({
        "simulated": True,
        "sim_signal_range": [-80, -40],
    })
    val = ant.read_signal()
    assert val is not None
    assert -80 <= val <= -40


def test_antenna_sim_varies():
    ant = AntennaReader({
        "simulated": True,
        "sim_signal_range": [-80, -40],
    })
    readings = {ant.read_signal() for _ in range(20)}
    assert len(readings) > 1  # not all the same value
