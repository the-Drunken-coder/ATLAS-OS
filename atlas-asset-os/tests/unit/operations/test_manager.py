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
                "type": "digital",
                "name": "Test Asset",
                "model_id": "test-model"
            }
        },
        "modules": {"operations": ops_cfg},
    }


def test_method_change_triggers_registration_once():
    """Test that asset registration is triggered on first method change only."""
    config = _base_config({
        "enabled": True,
        "heartbeat_interval_s": 30.0,
        "checkin_interval_s": 30.0,
        "checkin_interval_wifi_s": 1.0,
        "checkin_interval_mesh_s": 15.0,
        "checkin_payload": {"latitude": 0.0, "longitude": 0.0}
    })
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
    config = _base_config({
        "enabled": True,
        "heartbeat_interval_s": 30.0,
        "checkin_interval_s": 30.0,
        "checkin_interval_wifi_s": 1.0,
        "checkin_interval_mesh_s": 15.0,
        "checkin_payload": {"latitude": 0.0, "longitude": 0.0}
    })
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
    config = _base_config({
        "enabled": True,
        "heartbeat_interval_s": 30.0,
        "checkin_interval_s": 30.0,
        "checkin_interval_wifi_s": 1.0,
        "checkin_interval_mesh_s": 15.0,
        "checkin_payload": {"latitude": 0.0, "longitude": 0.0}
    })
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
    config = _base_config({
        "enabled": True,
        "heartbeat_interval_s": 30.0,
        "checkin_interval_s": 30.0,
        "checkin_interval_wifi_s": 1.0,
        "checkin_interval_mesh_s": 15.0,
        "checkin_payload": {"latitude": 0.0, "longitude": 0.0}
    })
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
    config = _base_config({
        "enabled": True,
        "heartbeat_interval_s": 30.0,
        "checkin_interval_s": 0,  # Disabled
        "checkin_interval_wifi_s": 1.0,
        "checkin_interval_mesh_s": 15.0,
        "checkin_payload": {"latitude": 0.0, "longitude": 0.0}
    })
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
    config = _base_config({
        "enabled": True,
        "heartbeat_interval_s": 30.0,
        "checkin_interval_s": 30.0,
        "checkin_interval_wifi_s": 1.0,
        "checkin_interval_mesh_s": 15.0,
        "checkin_payload": {"latitude": 0.0, "longitude": 0.0}
    })
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
    config = _base_config({
        "enabled": True,
        "heartbeat_interval_s": 30.0,
        "checkin_interval_s": 30.0,
        "checkin_interval_wifi_s": 1.0,
        "checkin_interval_mesh_s": 15.0,
        "checkin_payload": {"latitude": 0.0, "longitude": 0.0}
    })
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
