"""Tests for CommsClient (simulated mode)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from comms import CommsClient


ASSET = {"id": "test-asset", "name": "Test", "type": "asset", "model_id": "sensor"}
SIM_CONFIG = {"simulated": True, "base_url": ""}


def _make_client():
    c = CommsClient(SIM_CONFIG, ASSET)
    c.connect()
    return c


def test_simulated_connect():
    c = _make_client()
    assert c._simulated is True
    assert c._client is None  # no async client in sim mode


def test_register_asset_simulated():
    c = _make_client()
    result = c.register_asset()
    assert result == {}


def test_checkin_returns_empty_list():
    c = _make_client()
    tasks = c.checkin({"latitude": 34.0, "longitude": -118.0, "heading_deg": 45.0})
    assert tasks == []


def test_create_entity_simulated():
    c = _make_client()
    result = c.create_entity(
        entity_id="track-001",
        entity_type="track",
        subtype="signal",
        alias="track-001",
    )
    assert result == {}


def test_start_task_simulated():
    c = _make_client()
    assert c.start_task("task-001") == {}


def test_complete_task_simulated():
    c = _make_client()
    assert c.complete_task("task-001", {"signal": -55.0}) == {}


def test_fail_task_simulated():
    c = _make_client()
    assert c.fail_task("task-001", "something broke") == {}


def test_close_simulated():
    c = _make_client()
    c.close()  # should not raise
    assert c._client is None
    assert c._loop is None
