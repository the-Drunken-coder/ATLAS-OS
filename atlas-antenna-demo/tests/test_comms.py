"""Tests for CommsClient (simulated mode)."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import comms as comms_module
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


def test_radio_checkin_returns_new_tasks(monkeypatch):
    mock_meshtastic_client = MagicMock()
    mock_meshtastic_client.health_check.return_value = SimpleNamespace(
        type="response",
        data={"result": {"status": "ok"}},
    )
    mock_meshtastic_client.checkin_entity.return_value = SimpleNamespace(
        type="response",
        data={
            "result": {
                "tasks": [
                    {"task_id": "task-001"},
                    {"task_id": "task-001"},
                    {"task_id": "task-002"},
                ]
            }
        },
    )

    monkeypatch.setattr(comms_module, "_HAS_MESHTASTIC_BRIDGE", True)
    monkeypatch.setattr(comms_module, "load_mode_profile", lambda _: {})
    monkeypatch.setattr(comms_module, "strategy_from_name", lambda _: None)
    monkeypatch.setattr(comms_module, "build_radio", lambda *_args: object())
    monkeypatch.setattr(comms_module, "MeshtasticTransport", lambda *_args, **_kwargs: MagicMock())
    monkeypatch.setattr(
        comms_module,
        "MeshtasticClient",
        lambda *_args, **_kwargs: mock_meshtastic_client,
    )

    comms_cfg = {"use_radio": True, "simulated": False}
    radio_cfg = {
        "simulated": True,
        "gateway_node_id": "gw-1",
        "timeout_s": 5,
        "max_retries": 1,
    }
    client = CommsClient(comms_cfg, ASSET, radio_cfg)
    client.connect()

    tasks = client.checkin({"latitude": 34.0, "longitude": -118.0, "heading_deg": 45.0})
    assert [task["task_id"] for task in tasks] == ["task-001", "task-002"]
