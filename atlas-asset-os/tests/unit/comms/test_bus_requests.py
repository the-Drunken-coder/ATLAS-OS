from framework.bus import MessageBus
from modules.comms.manager import CommsManager


def _base_config() -> dict:
    return {
        "atlas": {"base_url": "http://localhost:8000", "api_token": None},
        "modules": {"comms": {"enabled": True}},
    }


def test_bus_request_success(monkeypatch):
    bus = MessageBus()
    manager = CommsManager(bus, _base_config())
    manager.client = object()

    responses = []

    def handler(data):
        responses.append(data)

    bus.subscribe("comms.response", handler)

    def ping(_client, **_kwargs):
        return {"ok": True}

    manager.functions = {"ping": lambda **kwargs: ping(manager.client, **kwargs)}

    manager._handle_bus_request({"function": "ping", "args": {}, "request_id": "req-1"})
    request = manager._dequeue_request()
    manager._process_request(request)

    assert responses
    assert responses[0]["ok"] is True
    assert responses[0]["function"] == "ping"
    assert responses[0]["request_id"] == "req-1"


def test_bus_request_error(monkeypatch):
    bus = MessageBus()
    manager = CommsManager(bus, _base_config())
    manager.client = object()

    responses = []

    def handler(data):
        responses.append(data)

    bus.subscribe("comms.response", handler)

    def fail(_client, **_kwargs):
        raise RuntimeError("boom")

    manager.functions = {"fail": lambda **kwargs: fail(manager.client, **kwargs)}

    manager._handle_bus_request({"function": "fail", "args": {}, "request_id": "req-2"})
    request = manager._dequeue_request()
    manager._process_request(request)

    assert responses
    assert responses[0]["ok"] is False
    assert responses[0]["function"] == "fail"
    assert responses[0]["request_id"] == "req-2"
