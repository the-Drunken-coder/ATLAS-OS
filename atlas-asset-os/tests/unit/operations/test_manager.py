import time
from unittest.mock import patch
from framework.bus import MessageBus
from modules.operations.manager import OperationsManager


def _base_config(ops_cfg: dict) -> dict:
    return {
        "atlas": {
            "base_url": "http://localhost:8000",
            "api_token": None,
            "asset": {
                "id": "test-asset-001",
                "type": "asset",
                "name": "Test Asset",
                "model_id": "test-model",
            },
        },
        "modules": {"operations": ops_cfg},
    }


def test_method_change_triggers_registration_once():
    """Test that asset registration is triggered on first method change only."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
            "checkin_interval_wifi_s": 1.0,
            "checkin_interval_mesh_s": 15.0,
            "checkin_payload": {"latitude": 0.0, "longitude": 0.0},
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    # Track calls to register_asset
    register_called = {"count": 0}

    def fake_register(b, c):
        register_called["count"] += 1
        return True

    with patch("modules.operations.manager.register_asset", fake_register):
        # Simulate first method change
        manager._handle_method_changed({"method": "wifi"})

        # Give thread time to start
        time.sleep(0.1)

        # Verify registration was called
        assert register_called["count"] == 1
        assert manager._registration_started is True

        # Simulate second method change
        manager._handle_method_changed({"method": "meshtastic"})

        # Give thread time to potentially start (it shouldn't)
        time.sleep(0.1)

        # Verify registration was NOT called again
        assert register_called["count"] == 1


def test_method_change_updates_checkin_interval():
    """Test that checkin interval is updated when method changes."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
            "checkin_interval_wifi_s": 1.0,
            "checkin_interval_mesh_s": 15.0,
            "checkin_payload": {"latitude": 0.0, "longitude": 0.0},
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    # Initial state should use default interval
    assert manager._current_checkin_interval_s == 30.0

    with patch("modules.operations.manager.register_asset", return_value=True):
        # Change to wifi
        manager._handle_method_changed({"method": "wifi"})
        assert manager._current_checkin_interval_s == 1.0

        # Change to meshtastic
        manager._handle_method_changed({"method": "meshtastic"})
        assert manager._current_checkin_interval_s == 15.0

        # Change to unknown method (should use default)
        manager._handle_method_changed({"method": "unknown"})
        assert manager._current_checkin_interval_s == 30.0


def test_method_change_preserves_checkin_timing():
    """Test that method change doesn't cause redundant check-ins."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
            "checkin_interval_wifi_s": 1.0,
            "checkin_interval_mesh_s": 15.0,
            "checkin_payload": {"latitude": 0.0, "longitude": 0.0},
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    with patch("modules.operations.manager.register_asset", return_value=True):
        # Simulate a recent check-in on mesh (15s interval)
        current_time = time.time()
        manager._current_method = "meshtastic"
        manager._current_checkin_interval_s = 15.0
        manager._last_checkin = current_time - 5.0  # Checked in 5 seconds ago

        # Switch to wifi (1s interval)
        # Since we're switching to a faster interval (1s) and 5s have elapsed,
        # we should be ready to check in immediately
        manager._handle_method_changed({"method": "wifi"})

        # The _last_checkin should be adjusted so next check-in happens immediately
        elapsed = time.time() - manager._last_checkin
        assert elapsed >= manager._current_checkin_interval_s

        # Now test the opposite: switch from fast to slow when we just checked in
        manager._last_checkin = time.time() - 0.5  # Just checked in 0.5s ago
        manager._current_method = "wifi"
        manager._current_checkin_interval_s = 1.0

        # Switch to mesh (15s interval)
        manager._handle_method_changed({"method": "meshtastic"})

        # The _last_checkin should be preserved - we don't want immediate check-in
        elapsed = time.time() - manager._last_checkin
        assert elapsed < 1.0  # Should still be less than 1 second


def test_method_change_ignores_duplicate_methods():
    """Test that duplicate method change events are ignored."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
            "checkin_interval_wifi_s": 1.0,
            "checkin_interval_mesh_s": 15.0,
            "checkin_payload": {"latitude": 0.0, "longitude": 0.0},
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    register_called = {"count": 0}

    def fake_register(b, c):
        register_called["count"] += 1
        return True

    with patch("modules.operations.manager.register_asset", fake_register):
        # First wifi change
        manager._handle_method_changed({"method": "wifi"})
        time.sleep(0.1)
        assert register_called["count"] == 1
        assert manager._current_checkin_interval_s == 1.0

        # Duplicate wifi change should be ignored
        manager._handle_method_changed({"method": "wifi"})
        time.sleep(0.1)
        assert register_called["count"] == 1  # Should not increment


def test_checkin_disabled_when_interval_zero():
    """Test that check-ins are disabled when interval is 0 or negative."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 0,  # Disabled
            "checkin_interval_wifi_s": 1.0,
            "checkin_interval_mesh_s": 15.0,
            "checkin_payload": {"latitude": 0.0, "longitude": 0.0},
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    # Default interval is 0, so checkins should be disabled
    assert manager._current_checkin_interval_s == 0

    # Publish events to track if check-ins happen
    checkin_requests = []

    def capture_checkin(data):
        checkin_requests.append(data)

    bus.subscribe("comms.request", capture_checkin)

    with patch("modules.operations.manager.register_asset", return_value=True):
        manager._registration_complete = True
        manager.start()

        # Wait a bit
        time.sleep(2)

        # No check-ins should have been sent
        assert len(checkin_requests) == 0

        manager.stop()


def test_registration_sets_completion_flag():
    """Test that registration completion flag is set correctly."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
            "checkin_interval_wifi_s": 1.0,
            "checkin_interval_mesh_s": 15.0,
            "checkin_payload": {"latitude": 0.0, "longitude": 0.0},
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    assert manager._registration_complete is False

    def fake_register(b, c):
        return True  # Success

    with patch("modules.operations.manager.register_asset", fake_register):
        manager._handle_method_changed({"method": "wifi"})

        # Wait for thread to complete
        time.sleep(0.2)

        # Registration should be complete
        assert manager._registration_complete is True


def test_registration_handles_failure():
    """Test that registration failure is handled gracefully."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
            "checkin_interval_wifi_s": 1.0,
            "checkin_interval_mesh_s": 15.0,
            "checkin_payload": {"latitude": 0.0, "longitude": 0.0},
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    def fake_register(b, c):
        return False  # Failure

    with patch("modules.operations.manager.register_asset", fake_register):
        manager._handle_method_changed({"method": "wifi"})

        # Wait for thread to complete
        time.sleep(0.2)

        # Registration should be marked as incomplete
        assert manager._registration_complete is False


def test_task_handling_enqueue_and_execute():
    """Test that tasks are properly enqueued and executed."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)
    manager.start()

    # Track comms requests
    comms_requests = []
    bus.subscribe("comms.request", lambda d: comms_requests.append(d))

    # Register a command handler
    executed_tasks = []

    def mock_handler(params):
        executed_tasks.append(params)
        return {"result": "success"}

    bus.publish(
        "commands.register", {"command": "test_command", "handler": mock_handler}
    )
    time.sleep(0.1)

    # Simulate receiving a task from checkin response
    manager._handle_comms_response(
        {
            "function": "checkin_entity",
            "ok": True,
            "result": {
                "tasks": [
                    {
                        "task_id": "task-123",
                        "status": "pending",
                        "components": {
                            "parameters": {
                                "command": "test_command",
                                "param1": "value1",
                            }
                        },
                    }
                ]
            },
        }
    )

    # Wait for task to be executed (loop will call _maybe_dispatch_command)
    time.sleep(1.5)

    # Verify handler was called
    assert len(executed_tasks) == 1
    assert executed_tasks[0]["param1"] == "value1"

    # Verify comms requests were made
    start_requests = [r for r in comms_requests if r.get("function") == "acknowledge_task"]
    complete_requests = [
        r for r in comms_requests if r.get("function") == "complete_task"
    ]

    assert len(start_requests) == 1
    assert start_requests[0]["args"]["task_id"] == "task-123"
    assert len(complete_requests) == 1
    assert complete_requests[0]["args"]["task_id"] == "task-123"

    manager.stop()


def test_task_handling_duplicate_filtering():
    """Test that duplicate tasks are filtered out."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)
    manager.start()

    executed_count = {"count": 0}

    def mock_handler(params):
        executed_count["count"] += 1
        return {}

    bus.publish("commands.register", {"command": "test_cmd", "handler": mock_handler})
    time.sleep(0.1)

    # Send same task twice
    task = {
        "task_id": "task-456",
        "status": "pending",
        "components": {"parameters": {"command": "test_cmd"}},
    }

    manager._handle_comms_response(
        {"function": "checkin_entity", "ok": True, "result": {"tasks": [task]}}
    )

    time.sleep(1.5)

    # Send same task again
    manager._handle_comms_response(
        {"function": "checkin_entity", "ok": True, "result": {"tasks": [task]}}
    )

    time.sleep(1.5)

    # Should only execute once
    assert executed_count["count"] == 1

    manager.stop()


def test_task_handling_error_handling():
    """Test that task errors are properly reported."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)
    manager.start()

    comms_requests = []
    bus.subscribe("comms.request", lambda d: comms_requests.append(d))

    def failing_handler(params):
        raise ValueError("Test error")

    bus.publish(
        "commands.register", {"command": "fail_cmd", "handler": failing_handler}
    )
    time.sleep(0.1)

    manager._handle_comms_response(
        {
            "function": "checkin_entity",
            "ok": True,
            "result": {
                "tasks": [
                    {
                        "task_id": "task-789",
                        "status": "pending",
                        "components": {"parameters": {"command": "fail_cmd"}},
                    }
                ]
            },
        }
    )

    time.sleep(1.5)

    # Verify fail_task was called
    fail_requests = [r for r in comms_requests if r.get("function") == "fail_task"]
    assert len(fail_requests) == 1
    assert fail_requests[0]["args"]["task_id"] == "task-789"
    assert "Test error" in fail_requests[0]["args"]["error_message"]

    manager.stop()


def test_track_broadcasting_distance_throttling():
    """Test that track updates are throttled based on distance."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
            "track_update_min_distance_m": 100.0,
            "track_update_min_seconds": 0.5,  # Use shorter time for test
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    comms_requests = []
    bus.subscribe("comms.request", lambda d: comms_requests.append(d))

    # First track update - should broadcast
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-1",
            "snapshot": {
                "tracks": {
                    "track-1": {
                        "value": {"latitude": 40.0, "longitude": -74.0},
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    time.sleep(0.6)  # Wait for time threshold

    # Second update with small distance change (< 100m) - should NOT broadcast
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-2",
            "snapshot": {
                "tracks": {
                    "track-1": {
                        "value": {"latitude": 40.0001, "longitude": -74.0},
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    time.sleep(0.6)  # Wait for time threshold

    # Third update with large distance change (> 100m) - should broadcast
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-3",
            "snapshot": {
                "tracks": {
                    "track-1": {
                        "value": {"latitude": 40.001, "longitude": -74.0},
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    time.sleep(0.1)

    # Count telemetry updates
    telemetry_updates = [
        r for r in comms_requests if r.get("function") == "update_telemetry"
    ]

    # Should have 2 updates: first one and third one (second was throttled due to distance)
    assert len(telemetry_updates) == 2


def test_track_broadcasting_time_throttling():
    """Test that track updates are throttled based on time."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
            "track_update_min_distance_m": 100.0,
            "track_update_min_seconds": 0.5,
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    comms_requests = []
    bus.subscribe("comms.request", lambda d: comms_requests.append(d))

    # First update
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-1",
            "snapshot": {
                "tracks": {
                    "track-2": {
                        "value": {"latitude": 40.0, "longitude": -74.0},
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    time.sleep(0.1)

    # Second update immediately (large distance change but too soon) - should NOT broadcast
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-2",
            "snapshot": {
                "tracks": {
                    "track-2": {
                        "value": {"latitude": 40.01, "longitude": -74.0},
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    time.sleep(0.5)

    # Third update after delay - should broadcast
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-3",
            "snapshot": {
                "tracks": {
                    "track-2": {
                        "value": {"latitude": 40.02, "longitude": -74.0},
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    time.sleep(0.1)

    # Count telemetry updates
    telemetry_updates = [
        r for r in comms_requests if r.get("function") == "update_telemetry"
    ]

    # Should have 2 updates: first one and third one
    assert len(telemetry_updates) == 2


def test_track_broadcasting_optional_fields():
    """Test that track broadcasts include optional fields when present."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    comms_requests = []
    bus.subscribe("comms.request", lambda d: comms_requests.append(d))

    # Track with all optional fields
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-1",
            "snapshot": {
                "tracks": {
                    "track-3": {
                        "value": {
                            "latitude": 40.0,
                            "longitude": -74.0,
                            "altitude_m": 100.5,
                            "speed_m_s": 15.2,
                            "heading_deg": 270.0,
                        },
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    time.sleep(0.1)

    # Verify optional fields are included
    telemetry_updates = [
        r for r in comms_requests if r.get("function") == "update_telemetry"
    ]
    assert len(telemetry_updates) == 1

    args = telemetry_updates[0]["args"]
    assert args["entity_id"] == "track-3"
    assert args["latitude"] == 40.0
    assert args["longitude"] == -74.0
    assert args["altitude_m"] == 100.5
    assert args["speed_m_s"] == 15.2
    assert args["heading_deg"] == 270.0


def test_track_broadcasting_handles_invalid_data():
    """Test that track broadcasting handles invalid data gracefully."""
    config = _base_config(
        {
            "enabled": True,
            "heartbeat_interval_s": 30.0,
            "checkin_interval_s": 30.0,
        }
    )
    bus = MessageBus()
    manager = OperationsManager(bus, config)

    comms_requests = []
    bus.subscribe("comms.request", lambda d: comms_requests.append(d))

    # Invalid snapshot data
    manager._handle_data_store_snapshot("invalid")
    manager._handle_data_store_snapshot({"snapshot": "invalid"})
    manager._handle_data_store_snapshot({"snapshot": {"tracks": "invalid"}})

    # Missing coordinates
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-1",
            "snapshot": {
                "tracks": {
                    "track-4": {
                        "value": {"latitude": 40.0},  # Missing longitude
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    # Invalid coordinate types
    manager._handle_data_store_snapshot(
        {
            "request_id": "snap-2",
            "snapshot": {
                "tracks": {
                    "track-5": {
                        "value": {"latitude": "invalid", "longitude": -74.0},
                        "updated_at": time.time(),
                    }
                }
            },
        }
    )

    time.sleep(0.1)

    # No telemetry updates should have been sent
    telemetry_updates = [
        r for r in comms_requests if r.get("function") == "update_telemetry"
    ]
    assert len(telemetry_updates) == 0
