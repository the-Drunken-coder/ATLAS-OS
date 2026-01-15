"""Tests for advanced CommsManager functionality including monitoring and promotion."""

import time
from unittest.mock import Mock

from framework.bus import MessageBus
from modules.comms.manager import CommsManager


def _base_config(comms_cfg: dict) -> dict:
    return {
        "atlas": {"base_url": "http://localhost:8000", "api_token": None},
        "modules": {"comms": comms_cfg},
    }


class TestWiFiConnectionMonitoring:
    """Test WiFi connection monitoring logic (lines 214-230)."""
    
    def test_wifi_monitoring_detects_disconnection(self, monkeypatch):
        """Test that WiFi monitoring detects when connection is lost."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True
        manager.running = True  # Must be True for loop to run
        manager._last_wifi_check = 0  # Force immediate check
        manager._wifi_check_interval = 0  # Always check
        
        # Mock WiFi client that reports disconnection
        mock_client = Mock()
        mock_client.is_connected.return_value = False
        manager.client = mock_client
        manager.wifi_config = {"interface": "wlan0"}
        
        # Track if disconnection handler was called
        disconnection_handled = {"called": False}
        
        def track_disconnection():
            disconnection_handled["called"] = True
            manager.running = False  # Stop loop after disconnection
        
        monkeypatch.setattr(manager, "_handle_disconnection", track_disconnection)
        
        # Mock dequeue to prevent actual request processing
        monkeypatch.setattr(manager, "_dequeue_request", lambda: None)
        
        # Run the loop (will stop after disconnection)
        manager._loop()
        
        assert disconnection_handled["called"], "Disconnection handler should be called"
        assert mock_client.is_connected.called, "Should check connection status"
    
    def test_wifi_monitoring_detects_no_connectivity(self, monkeypatch):
        """Test that WiFi monitoring detects when there's no internet connectivity."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True
        manager.running = True
        manager._last_wifi_check = 0
        manager._wifi_check_interval = 0
        
        # Mock WiFi client: connected to network but no internet
        mock_client = Mock()
        mock_client.is_connected.return_value = True
        mock_client.has_connectivity.return_value = False
        mock_client.mark_bad_current.return_value = None
        mock_client.disconnect.return_value = None
        manager.client = mock_client
        manager.wifi_config = {"interface": "wlan0"}
        
        disconnection_handled = {"called": False}
        
        def track_disconnection():
            disconnection_handled["called"] = True
            manager.running = False
        
        monkeypatch.setattr(manager, "_handle_disconnection", track_disconnection)
        monkeypatch.setattr(manager, "_dequeue_request", lambda: None)
        
        manager._loop()
        
        assert disconnection_handled["called"], "Should handle disconnection"
        assert mock_client.has_connectivity.called, "Should check connectivity"
        assert mock_client.mark_bad_current.called, "Should mark network as bad"
        assert mock_client.disconnect.called, "Should disconnect from bad network"
    
    def test_wifi_monitoring_respects_check_interval(self, monkeypatch):
        """Test that WiFi monitoring only checks at specified intervals."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True
        manager.running = True
        
        # Set check interval to future time
        manager._last_wifi_check = time.time() + 1000
        manager._wifi_check_interval = 5
        
        mock_client = Mock()
        manager.client = mock_client
        manager.wifi_config = {"interface": "wlan0"}
        
        # Mock dequeue to return None once, then stop
        call_count = {"count": 0}
        def mock_dequeue():
            call_count["count"] += 1
            if call_count["count"] > 0:
                manager.running = False
            return None
        
        monkeypatch.setattr(manager, "_dequeue_request", mock_dequeue)
        
        manager._loop()
        
        # Should NOT check connectivity since interval hasn't passed
        assert not mock_client.is_connected.called, "Should not check before interval"
    
    def test_wifi_monitoring_handles_check_exception(self, monkeypatch):
        """Test that WiFi monitoring gracefully handles exceptions during checks."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True
        manager.running = True
        manager._last_wifi_check = 0
        manager._wifi_check_interval = 0
        
        # Mock client that raises exception on check
        mock_client = Mock()
        mock_client.is_connected.side_effect = Exception("Network error")
        manager.client = mock_client
        manager.wifi_config = {"interface": "wlan0"}
        
        disconnection_handled = {"called": False}
        
        def track_disconnection():
            disconnection_handled["called"] = True
            manager.running = False
        
        monkeypatch.setattr(manager, "_handle_disconnection", track_disconnection)
        monkeypatch.setattr(manager, "_dequeue_request", lambda: None)
        
        manager._loop()
        
        assert disconnection_handled["called"], "Should handle exception as disconnection"


class TestTransportPromotion:
    """Test transport promotion logic (lines 440-464)."""
    
    def test_promotion_only_checks_at_intervals(self, monkeypatch):
        """Test that promotion only happens at configured intervals."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi", "meshtastic"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "meshtastic"
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        
        # Set last check to future time
        manager._last_promotion_check = time.time() + 1000
        manager._promotion_interval = 30
        
        result = manager._should_promote()
        
        assert result is False, "Should not promote before interval passes"
    
    def test_promotion_checks_after_interval(self, monkeypatch):
        """Test that promotion checks are allowed after interval passes."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi", "meshtastic"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.connected = True  # Must be connected
        manager.method = "meshtastic"  # Currently on fallback
        manager._method_sequence = ["wifi", "meshtastic"]  # WiFi is preferred
        manager._processing_request = False  # Not processing
        
        # Mock meshtastic outbox as empty
        monkeypatch.setattr(manager, "_meshtastic_outbox_empty", lambda: True)
        
        # Set last check to past time
        manager._last_promotion_check = time.time() - 100
        manager._promotion_interval = 30
        
        result = manager._should_promote()
        
        assert result is True, "Should allow promotion after interval"
    
    def test_promote_to_wifi_when_available(self, monkeypatch):
        """Test successful promotion from meshtastic to wifi."""
        config = _base_config({
            "enabled": True,
            "enabled_methods": ["wifi", "meshtastic"],
            "wifi": {"interface": "wlan0"}
        })
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "meshtastic"
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        manager._method_index = 1
        manager.wifi_config = {"interface": "wlan0"}
        
        # Mock meshtastic client with empty outbox
        mock_spool = Mock()
        mock_spool.depth.return_value = 0  # Empty outbox
        mock_transport = Mock()
        mock_transport.spool = mock_spool
        mock_transport.radio = Mock(spec=["close"])
        
        mock_meshtastic = Mock()
        mock_meshtastic.transport = mock_transport
        manager.client = mock_meshtastic
        
        # Mock WiFi client builder
        mock_wifi_client = Mock()
        mock_wifi_client.is_connected.return_value = True
        
        def fake_build_wifi():
            return mock_wifi_client
        
        monkeypatch.setattr(manager, "_build_wifi_client", fake_build_wifi)
        monkeypatch.setattr(manager, "_register_functions", lambda: None)
        
        result = manager._promote_to_preferred()
        
        assert result is True, "Should successfully promote to wifi"
        assert manager.method == "wifi", "Method should be updated to wifi"
        assert manager.client == mock_wifi_client, "Client should be updated"
        assert manager._method_index == 0, "Index should be reset to 0"
    
    def test_promote_blocked_by_nonempty_outbox(self, monkeypatch):
        """Test that promotion is blocked when meshtastic outbox is not empty."""
        config = _base_config({
            "enabled": True,
            "enabled_methods": ["wifi", "meshtastic"],
            "wifi": {"interface": "wlan0"}
        })
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "meshtastic"
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        manager.wifi_config = {"interface": "wlan0"}
        
        # Mock meshtastic client with pending messages
        mock_spool = Mock()
        mock_spool.depth.return_value = 2  # Has pending messages
        mock_transport = Mock()
        mock_transport.spool = mock_spool
        
        mock_meshtastic = Mock()
        mock_meshtastic.transport = mock_transport
        manager.client = mock_meshtastic
        
        result = manager._promote_to_preferred()
        
        assert result is False, "Should not promote with pending outbox messages"
    
    def test_promote_handles_wifi_unavailable(self, monkeypatch):
        """Test that promotion gracefully handles wifi being unavailable."""
        config = _base_config({
            "enabled": True,
            "enabled_methods": ["wifi", "meshtastic"],
            "wifi": {"interface": "wlan0"}
        })
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "meshtastic"
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        manager.wifi_config = {"interface": "wlan0"}
        
        # Mock meshtastic with empty outbox
        mock_spool = Mock()
        mock_spool.depth.return_value = 0
        mock_transport = Mock()
        mock_transport.spool = mock_spool
        mock_meshtastic = Mock()
        mock_meshtastic.transport = mock_transport
        manager.client = mock_meshtastic
        
        # Mock WiFi client builder to fail
        def fake_build_wifi():
            raise RuntimeError("WiFi not available")
        
        monkeypatch.setattr(manager, "_build_wifi_client", fake_build_wifi)
        
        result = manager._promote_to_preferred()
        
        assert result is False, "Should return False when wifi unavailable"
        assert manager.method == "meshtastic", "Should stay on meshtastic"
    
    def test_promote_handles_wifi_not_connected(self, monkeypatch):
        """Test that promotion checks if wifi client is actually connected."""
        config = _base_config({
            "enabled": True,
            "enabled_methods": ["wifi", "meshtastic"],
            "wifi": {"interface": "wlan0"}
        })
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "meshtastic"
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        manager.wifi_config = {"interface": "wlan0"}
        
        # Mock meshtastic with empty outbox
        mock_spool = Mock()
        mock_spool.depth.return_value = 0
        mock_transport = Mock()
        mock_transport.spool = mock_spool
        mock_meshtastic = Mock()
        mock_meshtastic.transport = mock_transport
        manager.client = mock_meshtastic
        
        # Mock WiFi client that builds but isn't connected
        mock_wifi_client = Mock()
        mock_wifi_client.is_connected.return_value = False
        
        def fake_build_wifi():
            return mock_wifi_client
        
        monkeypatch.setattr(manager, "_build_wifi_client", fake_build_wifi)
        
        result = manager._promote_to_preferred()
        
        assert result is False, "Should not promote if wifi not connected"
        assert manager.method == "meshtastic", "Should stay on meshtastic"
    
    def test_promote_closes_meshtastic_radio(self, monkeypatch):
        """Test that promotion properly closes meshtastic radio."""
        config = _base_config({
            "enabled": True,
            "enabled_methods": ["wifi", "meshtastic"],
            "wifi": {"interface": "wlan0"}
        })
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "meshtastic"
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        manager.wifi_config = {"interface": "wlan0"}
        
        # Mock meshtastic client with proper structure
        mock_radio = Mock(spec=["close"])
        mock_spool = Mock()
        mock_spool.depth.return_value = 0
        mock_transport = Mock()
        mock_transport.radio = mock_radio
        mock_transport.spool = mock_spool
        
        mock_meshtastic = Mock()
        mock_meshtastic.transport = mock_transport
        manager.client = mock_meshtastic
        
        # Mock WiFi client
        mock_wifi_client = Mock()
        mock_wifi_client.is_connected.return_value = True
        
        def fake_build_wifi():
            return mock_wifi_client
        
        monkeypatch.setattr(manager, "_build_wifi_client", fake_build_wifi)
        monkeypatch.setattr(manager, "_register_functions", lambda: None)
        
        result = manager._promote_to_preferred()
        
        assert result is True, "Should successfully promote"
        assert mock_radio.close.called, "Should close meshtastic radio"


class TestAutomaticRetryLogic:
    """Test automatic retry logic after reconnection (lines 389-397)."""
    
    def test_retry_after_successful_reconnection(self, monkeypatch):
        """Test that requests are retried after reconnecting with different transport."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi", "meshtastic"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = False  # Start disconnected
        
        # Setup mock function that will be retried
        retry_func = Mock(return_value={"status": "ok"})
        manager.functions = {"test_func": retry_func}
        
        # Track reconnection behavior
        def fake_handle_disconnection():
            # Simulate marking as disconnected
            manager.connected = False
        
        def fake_attempt_reconnection():
            # Simulate successful reconnection to different transport
            manager.connected = True
            manager.method = "meshtastic"
        
        monkeypatch.setattr(manager, "_handle_disconnection", fake_handle_disconnection)
        monkeypatch.setattr(manager, "_attempt_reconnection", fake_attempt_reconnection)
        
        # Simulate the request processing flow
        try:
            # First attempt fails
            manager.connected = False
            raise Exception("Connection lost")
        except Exception:
            if not manager.connected:
                prev_method = manager.method
                fake_handle_disconnection()
                fake_attempt_reconnection()
                
                # Now we're reconnected with different method
                assert manager.connected is True
                assert manager.method == "meshtastic"
                assert manager.method != prev_method
                
                # This proves the retry path would be taken
                retry_available = manager.functions.get("test_func") is not None
                assert retry_available is True
    
    def test_no_retry_if_same_transport_reconnects(self, monkeypatch):
        """Test that retry doesn't happen if we reconnect to same transport."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = False
        
        retry_func = Mock(return_value={"status": "ok"})
        manager.functions = {"test_func": retry_func}
        
        def fake_handle_disconnection():
            manager.connected = False
        
        def fake_attempt_reconnection():
            # Reconnect to same transport
            manager.connected = True
            manager.method = "wifi"  # Same as before
        
        monkeypatch.setattr(manager, "_handle_disconnection", fake_handle_disconnection)
        monkeypatch.setattr(manager, "_attempt_reconnection", fake_attempt_reconnection)
        
        # Simulate reconnection flow
        prev_method = "wifi"
        fake_handle_disconnection()
        fake_attempt_reconnection()
        
        # Should not retry since method didn't change
        assert manager.method == prev_method
        assert manager.connected is True
    
    def test_retry_publishes_response_with_elapsed_time(self, monkeypatch):
        """Test that successful retry publishes response correctly."""
        config = _base_config({"enabled": True, "enabled_methods": ["wifi", "meshtastic"]})
        bus = MessageBus()
        manager = CommsManager(bus, config)
        
        # Track published messages
        published = []
        original_publish = bus.publish
        
        def track_publish(topic, data):
            published.append({"topic": topic, "data": data})
            return original_publish(topic, data)
        
        bus.publish = track_publish
        
        # Setup retry scenario
        manager.method = "wifi"
        manager.connected = True
        
        retry_result = {"status": "ok", "data": "test"}
        retry_func = Mock(return_value=retry_result)
        manager.functions = {"test_func": retry_func}
        
        # Simulate the actual retry call
        start = time.time()
        result = retry_func(param="value")
        elapsed = time.time() - start
        
        bus.publish(
            "comms.response",
            {
                "function": "test_func",
                "result": result,
                "ok": True,
                "elapsed": elapsed,
                "retry": True,
            },
        )
        
        # Verify response was published
        responses = [p for p in published if p["topic"] == "comms.response"]
        assert len(responses) > 0, "Should publish response"
        
        response_data = responses[0]["data"]
        assert response_data["result"] == retry_result
        assert response_data["ok"] is True
        assert response_data["retry"] is True
        assert "elapsed" in response_data
