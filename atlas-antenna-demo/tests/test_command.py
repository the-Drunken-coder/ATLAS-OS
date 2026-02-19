"""Tests for handle_task and do_get_signal_strength."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from antenna import AntennaReader
from comms import CommsClient
from gps import GpsReader
from start import do_get_signal_strength, handle_task


GPS_CFG = {
    "simulated": True, "interval_s": 0.1,
    "sim_start_lat": 34.0522, "sim_start_lon": -118.2437,
    "sim_heading_deg": 45.0, "sim_speed_m_s": 1.4,
}
ANT_CFG = {"simulated": True, "sim_signal_range": [-80, -40]}
COMMS_CFG = {"simulated": True, "base_url": ""}
ASSET_CFG = {"id": "test-001", "name": "Test", "type": "asset", "model_id": "sensor"}
APP_CFG = {
    "asset": ASSET_CFG,
    "track_offset_m": 12.192,
    "track_subtype": "signal",
    "track_alias_prefix": "sig-track",
}


def _setup():
    gps = GpsReader(GPS_CFG)
    gps.start()
    time.sleep(0.3)  # let sim produce a fix
    antenna = AntennaReader(ANT_CFG)
    comms = CommsClient(COMMS_CFG, ASSET_CFG)
    comms.connect()
    return gps, antenna, comms


def test_do_get_signal_strength():
    gps, antenna, comms = _setup()
    try:
        result = do_get_signal_strength(gps, antenna, comms, APP_CFG)

        assert "signal_strength_dbm" in result
        assert -80 <= result["signal_strength_dbm"] <= -40
        assert "track_entity_id" in result
        assert result["track_entity_id"].startswith("sig-track-")
        assert "track_position" in result
        assert "latitude" in result["track_position"]
        assert "longitude" in result["track_position"]
        assert "source_position" in result
        assert result["offset_m"] == 12.192
    finally:
        gps.stop()


def test_track_position_differs_from_source():
    gps, antenna, comms = _setup()
    try:
        result = do_get_signal_strength(gps, antenna, comms, APP_CFG)
        tp = result["track_position"]
        sp = result["source_position"]
        # Track should be offset from source
        assert tp["latitude"] != sp["latitude"] or tp["longitude"] != sp["longitude"]
    finally:
        gps.stop()


def test_handle_task_known_command():
    gps, antenna, comms = _setup()
    try:
        task = {
            "task_id": "task-abc",
            "components": {"command_name": "get_signal_strength", "parameters": {}},
            "extra": {"command_definition_id": "get_signal_strength"},
        }
        # Should not raise — simulated comms just logs
        handle_task(task, gps, antenna, comms, APP_CFG)
    finally:
        gps.stop()


def test_handle_task_unknown_command():
    gps, antenna, comms = _setup()
    try:
        task = {
            "task_id": "task-xyz",
            "components": {"command_name": "do_something_else", "parameters": {}},
            "extra": {"command_definition_id": "do_something_else"},
        }
        # Should not raise — logs warning and fails task via simulated comms
        handle_task(task, gps, antenna, comms, APP_CFG)
    finally:
        gps.stop()


def test_handle_task_fallback_to_extra():
    """Command name missing from components — falls back to extra.command_definition_id."""
    gps, antenna, comms = _setup()
    try:
        task = {
            "task_id": "task-fallback",
            "components": {"parameters": {}},
            "extra": {"command_definition_id": "get_signal_strength"},
        }
        handle_task(task, gps, antenna, comms, APP_CFG)
    finally:
        gps.stop()
