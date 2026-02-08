"""Tests for asset registration module."""

import threading
import time


from framework.bus import MessageBus
from modules.operations.registration import register_asset


def _base_config(asset_cfg: dict) -> dict:
    """Create a base configuration for testing."""
    return {
        "atlas": {
            "base_url": "http://localhost:8000",
            "api_token": None,
            "asset": asset_cfg,
        },
    }


def _simulate_success_response(bus: MessageBus, delay: float = 0.1):
    """Simulate a successful response from the comms bus."""

    def on_request(data):
        req_id = data.get("request_id") if isinstance(data, dict) else None

        def send_response():
            time.sleep(delay)
            bus.publish(
                "comms.response",
                {
                    "function": "create_entity",
                    "request_id": req_id,
                    "ok": True,
                },
            )

        threading.Thread(target=send_response, daemon=True).start()

    bus.subscribe("comms.request", on_request)


def _simulate_error_response(
    bus: MessageBus, error_msg: str = "Test error", delay: float = 0.1
):
    """Simulate an error response from the comms bus."""

    def on_request(data):
        req_id = data.get("request_id") if isinstance(data, dict) else None

        def send_response():
            time.sleep(delay)
            bus.publish(
                "comms.response",
                {
                    "function": "create_entity",
                    "request_id": req_id,
                    "ok": False,
                    "error": error_msg,
                },
            )

        threading.Thread(target=send_response, daemon=True).start()

    bus.subscribe("comms.request", on_request)


def test_register_asset_with_valid_asset_type():
    """Test that asset registration succeeds with valid asset type."""
    config = _base_config(
        {
            "id": "test-asset-001",
            "type": "asset",
            "name": "Test Asset",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()
    _simulate_success_response(bus)

    result = register_asset(bus, config, timeout=1.0)
    assert result is True


def test_register_asset_with_valid_track_type():
    """Test that asset registration succeeds with track entity type."""
    config = _base_config(
        {
            "id": "test-track-001",
            "type": "track",
            "name": "Test Track",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()
    _simulate_success_response(bus)

    result = register_asset(bus, config, timeout=1.0)
    assert result is True


def test_register_asset_with_valid_geofeature_type():
    """Test that asset registration succeeds with geofeature entity type."""
    config = _base_config(
        {
            "id": "test-geofeature-001",
            "type": "geofeature",
            "name": "Test Geofeature",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()
    _simulate_success_response(bus)

    result = register_asset(bus, config, timeout=1.0)
    assert result is True


def test_register_asset_with_invalid_entity_type():
    """Test that asset registration fails with invalid entity type."""
    config = _base_config(
        {
            "id": "test-asset-001",
            "type": "invalid_type",
            "name": "Test Asset",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()

    result = register_asset(bus, config, timeout=1.0)

    # Should fail without making comms request
    assert result is False


def test_register_asset_normalizes_type_to_lowercase():
    """Test that entity type is normalized to lowercase."""
    config = _base_config(
        {
            "id": "test-asset-001",
            "type": "ASSET",
            "name": "Test Asset",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()

    # Track what was published to the bus
    published_data = []

    def track_publish(topic, data):
        if topic == "comms.request":
            published_data.append(data)

    original_publish = bus.publish
    bus.publish = lambda topic, data: (
        track_publish(topic, data),
        original_publish(topic, data),
    )[1]

    _simulate_success_response(bus)
    result = register_asset(bus, config, timeout=1.0)

    assert result is True
    # Verify the request was made with lowercase type
    assert len(published_data) > 0
    assert published_data[0]["args"]["entity_type"] == "asset"


def test_register_asset_with_mixed_case_type():
    """Test that mixed case entity types are normalized to lowercase."""
    config = _base_config(
        {
            "id": "test-track-001",
            "type": "Track",
            "name": "Test Track",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()

    published_data = []

    def track_publish(topic, data):
        if topic == "comms.request":
            published_data.append(data)

    original_publish = bus.publish
    bus.publish = lambda topic, data: (
        track_publish(topic, data),
        original_publish(topic, data),
    )[1]

    _simulate_success_response(bus)
    result = register_asset(bus, config, timeout=1.0)

    assert result is True
    assert len(published_data) > 0
    assert published_data[0]["args"]["entity_type"] == "track"


def test_register_asset_defaults_to_asset_type():
    """Test that missing type defaults to 'asset'."""
    config = _base_config(
        {
            "id": "test-asset-001",
            "name": "Test Asset",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()

    published_data = []

    def track_publish(topic, data):
        if topic == "comms.request":
            published_data.append(data)

    original_publish = bus.publish
    bus.publish = lambda topic, data: (
        track_publish(topic, data),
        original_publish(topic, data),
    )[1]

    _simulate_success_response(bus)
    result = register_asset(bus, config, timeout=1.0)

    assert result is True
    assert len(published_data) > 0
    assert published_data[0]["args"]["entity_type"] == "asset"


def test_register_asset_fails_without_asset_id():
    """Test that registration fails when asset ID is missing."""
    config = _base_config(
        {
            "type": "asset",
            "name": "Test Asset",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()

    result = register_asset(bus, config, timeout=1.0)
    assert result is False


def test_register_asset_fails_without_asset_config():
    """Test that registration fails when asset config is missing."""
    config = {
        "atlas": {
            "base_url": "http://localhost:8000",
            "api_token": None,
        },
    }
    bus = MessageBus()

    result = register_asset(bus, config, timeout=1.0)
    assert result is False


def test_register_asset_handles_error_response():
    """Test that registration handles error responses gracefully."""
    config = _base_config(
        {
            "id": "test-asset-001",
            "type": "asset",
            "name": "Test Asset",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()
    _simulate_error_response(bus, "Server error")

    result = register_asset(bus, config, timeout=1.0)
    assert result is False


def test_register_asset_validates_allowed_types():
    """Test that only allowed entity types (asset, track, geofeature) pass validation."""
    allowed_types = ["asset", "track", "geofeature"]
    invalid_types = ["entity", "sensor", "command", "object", "model"]

    for entity_type in allowed_types:
        config = _base_config(
            {
                "id": f"test-{entity_type}-001",
                "type": entity_type,
                "name": f"Test {entity_type}",
                "model_id": "test-model",
            }
        )
        bus = MessageBus()
        _simulate_success_response(bus)

        result = register_asset(bus, config, timeout=1.0)
        assert result is True, f"Expected {entity_type} to be allowed"

    for entity_type in invalid_types:
        config = _base_config(
            {
                "id": f"test-{entity_type}-001",
                "type": entity_type,
                "name": f"Test {entity_type}",
                "model_id": "test-model",
            }
        )
        bus = MessageBus()

        result = register_asset(bus, config, timeout=1.0)
        assert result is False, f"Expected {entity_type} to be rejected"


def test_register_asset_ignores_unrelated_request_id():
    """Test that registration ignores responses with a different request_id."""
    config = _base_config(
        {
            "id": "test-asset-001",
            "type": "asset",
            "name": "Test Asset",
            "model_id": "test-model",
        }
    )
    bus = MessageBus()

    # Send a response with a mismatched request_id
    def send_wrong_response(data):
        if not isinstance(data, dict) or data.get("function") != "create_entity":
            return

        def respond():
            time.sleep(0.05)
            bus.publish(
                "comms.response",
                {
                    "function": "create_entity",
                    "request_id": "wrong-id",
                    "ok": True,
                },
            )

        threading.Thread(target=respond, daemon=True).start()

    bus.subscribe("comms.request", send_wrong_response)

    result = register_asset(bus, config, timeout=0.5)
    # Should time out because the request_id doesn't match
    assert result is False
