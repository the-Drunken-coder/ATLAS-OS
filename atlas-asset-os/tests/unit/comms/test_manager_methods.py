from framework.bus import MessageBus
from modules.comms.manager import CommsManager


def _base_config(comms_cfg: dict) -> dict:
    return {
        "atlas": {"base_url": "http://localhost:8000", "api_token": None},
        "modules": {"comms": comms_cfg},
    }


def test_method_selection_respects_enabled_methods(monkeypatch):
    config = _base_config({"enabled": True, "enabled_methods": ["meshtastic"]})
    bus = MessageBus()
    manager = CommsManager(bus, config)
    manager.priority_methods = ["wifi", "meshtastic"]

    called = {"wifi": 0, "meshtastic": 0}

    def fake_wifi():
        called["wifi"] += 1
        return False

    def fake_meshtastic():
        called["meshtastic"] += 1
        manager.method = "meshtastic"
        manager.connected = True
        return True

    monkeypatch.setattr(manager, "_init_wifi", fake_wifi)
    monkeypatch.setattr(manager, "_init_meshtastic", fake_meshtastic)

    manager._init_bridge()

    assert called["wifi"] == 0
    assert called["meshtastic"] == 1
    assert manager.method == "meshtastic"
    assert manager.connected is True


def test_method_selection_falls_back_when_primary_fails(monkeypatch):
    config = _base_config({"enabled": True, "enabled_methods": ["wifi", "meshtastic"]})
    bus = MessageBus()
    manager = CommsManager(bus, config)
    manager.priority_methods = ["wifi", "meshtastic"]

    def fake_wifi():
        return False

    def fake_meshtastic():
        manager.method = "meshtastic"
        manager.connected = True
        return True

    monkeypatch.setattr(manager, "_init_wifi", fake_wifi)
    monkeypatch.setattr(manager, "_init_meshtastic", fake_meshtastic)

    manager._init_bridge()

    assert manager.method == "meshtastic"
    assert manager.connected is True


def test_method_selection_handles_all_failures(monkeypatch):
    config = _base_config({"enabled": True, "enabled_methods": ["wifi"]})
    bus = MessageBus()
    manager = CommsManager(bus, config)
    manager.priority_methods = ["wifi"]

    def fake_wifi():
        return False

    monkeypatch.setattr(manager, "_init_wifi", fake_wifi)

    manager._init_bridge()

    assert manager.method is None
    assert manager.connected is False
