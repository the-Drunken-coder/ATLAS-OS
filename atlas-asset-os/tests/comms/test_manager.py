"""Tests for the CommsManager module."""

import time
from unittest.mock import MagicMock, patch

import pytest


class TestCommsManagerInit:
    """Tests for CommsManager initialization."""

    def test_init_default_config(self):
        """Test CommsManager initializes with default config values."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}

        manager = CommsManager(bus, config)

        assert manager.simulated is False
        assert manager.gateway_node_id == "gateway"
        assert manager.method is None
        assert manager.connected is False
        assert manager._reconnect_attempts == 0

    def test_init_with_simulated_mode(self):
        """Test CommsManager initializes in simulated mode."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {"simulated": True}}}

        manager = CommsManager(bus, config)

        assert manager.simulated is True

    def test_init_with_custom_gateway_node_id(self):
        """Test CommsManager uses custom gateway_node_id."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {"gateway_node_id": "custom_gateway"}}}

        manager = CommsManager(bus, config)

        assert manager.gateway_node_id == "custom_gateway"

    def test_init_with_enabled_methods(self):
        """Test CommsManager parses enabled_methods config."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {"enabled_methods": ["wifi", "meshtastic"]}}}

        manager = CommsManager(bus, config)

        assert manager.enabled_methods == ["wifi", "meshtastic"]

    def test_init_with_legacy_method_config(self):
        """Test CommsManager supports legacy 'method' config."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {"method": "wifi"}}}

        manager = CommsManager(bus, config)

        assert manager.enabled_methods == ["wifi"]

    def test_init_with_radio_port_auto(self):
        """Test CommsManager treats 'auto' as None for radio_port."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {"radio_port": "auto"}}}

        manager = CommsManager(bus, config)

        assert manager.radio_port is None

    def test_init_with_explicit_radio_port(self):
        """Test CommsManager uses explicit radio_port."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {"radio_port": "/dev/ttyUSB0"}}}

        manager = CommsManager(bus, config)

        assert manager.radio_port == "/dev/ttyUSB0"


class TestCommsManagerMethods:
    """Tests for CommsManager methods."""

    def test_resolve_enabled_methods_from_list(self):
        """Test _resolve_enabled_methods parses list correctly."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)

        result = manager._resolve_enabled_methods({"enabled_methods": ["wifi", "meshtastic"]})

        assert result == ["wifi", "meshtastic"]

    def test_resolve_enabled_methods_from_legacy(self):
        """Test _resolve_enabled_methods handles legacy 'method' key."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)

        result = manager._resolve_enabled_methods({"method": "meshtastic"})

        assert result == ["meshtastic"]

    def test_resolve_enabled_methods_returns_none_when_empty(self):
        """Test _resolve_enabled_methods returns None when no methods configured."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)

        result = manager._resolve_enabled_methods({})

        assert result is None

    def test_iter_methods_filters_by_enabled(self):
        """Test _iter_methods filters by enabled_methods."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {"enabled_methods": ["wifi"]}}}
        manager = CommsManager(bus, config)
        manager.priority_methods = ["meshtastic", "wifi"]

        result = manager._iter_methods()

        assert result == ["wifi"]

    def test_iter_methods_returns_priority_when_no_filter(self):
        """Test _iter_methods returns priority_methods when no filter."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.priority_methods = ["meshtastic", "wifi"]
        manager.enabled_methods = None

        result = manager._iter_methods()

        assert result == ["meshtastic", "wifi"]

    def test_build_status_payload_wifi(self):
        """Test _build_status_payload for wifi method."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True
        manager.wifi_config = {"interface": "wlan0", "ssid": "TestNetwork"}

        payload = manager._build_status_payload()

        assert payload["method"] == "wifi"
        assert payload["connected"] is True
        assert payload["transport"]["interface"] == "wlan0"
        assert payload["transport"]["ssid"] == "TestNetwork"

    def test_build_status_payload_meshtastic(self):
        """Test _build_status_payload for meshtastic method."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.method = "meshtastic"
        manager.connected = True
        manager.radio_port = "/dev/ttyUSB0"
        manager.gateway_node_id = "gateway"
        manager.mode = "general"
        manager.simulated = False

        payload = manager._build_status_payload()

        assert payload["method"] == "meshtastic"
        assert payload["connected"] is True
        assert payload["transport"]["radio_port"] == "/dev/ttyUSB0"
        assert payload["transport"]["gateway_node_id"] == "gateway"

    def test_build_status_payload_with_request_id(self):
        """Test _build_status_payload includes request_id when provided."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True

        payload = manager._build_status_payload(request_id="req-123")

        assert payload["request_id"] == "req-123"

    def test_register_functions_clears_when_not_connected(self):
        """Test _register_functions clears functions when not connected."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.functions = {"test": lambda: None}
        manager.connected = False
        manager.client = None

        manager._register_functions()

        assert manager.functions == {}

    def test_register_functions_populates_when_connected(self):
        """Test _register_functions populates functions when connected."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.connected = True
        manager.client = MagicMock()

        manager._register_functions()

        # Should have registered functions from FUNCTION_REGISTRY
        assert len(manager.functions) > 0

    def test_handle_bus_request_enqueues_data(self):
        """Test _handle_bus_request adds data to queue."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)

        manager._handle_bus_request({"function": "test", "args": {}})

        assert len(manager._request_queue) == 1
        assert manager._request_queue[0] == {"function": "test", "args": {}}

    def test_handle_bus_request_ignores_empty_data(self):
        """Test _handle_bus_request ignores empty data."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)

        manager._handle_bus_request(None)
        manager._handle_bus_request({})

        assert len(manager._request_queue) == 0

    def test_dequeue_request_returns_none_when_empty(self):
        """Test _dequeue_request returns None when queue is empty."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)

        result = manager._dequeue_request()

        assert result is None

    def test_dequeue_request_returns_item(self):
        """Test _dequeue_request returns and removes item from queue."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager._request_queue.append({"function": "test"})

        result = manager._dequeue_request()

        assert result == {"function": "test"}
        assert len(manager._request_queue) == 0


class TestCommsManagerSystemCheck:
    """Tests for CommsManager system_check method."""

    def test_system_check_healthy_when_connected(self):
        """Test system_check reports healthy when connected."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.running = True
        manager.connected = True
        manager.method = "wifi"
        manager._thread = MagicMock()
        manager._thread.is_alive.return_value = True

        result = manager.system_check()

        assert result["healthy"] is True
        assert result["status"] == "connected"
        assert result["method"] == "wifi"

    def test_system_check_unhealthy_when_disconnected(self):
        """Test system_check reports unhealthy when disconnected."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.running = True
        manager.connected = False
        manager._thread = MagicMock()
        manager._thread.is_alive.return_value = True

        result = manager.system_check()

        assert result["healthy"] is False
        assert result["status"] == "disconnected"

    def test_system_check_unhealthy_when_not_running(self):
        """Test system_check reports unhealthy when not running."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.running = False
        manager.connected = True

        result = manager.system_check()

        assert result["healthy"] is False


class TestCommsManagerStartStop:
    """Tests for CommsManager start/stop lifecycle."""

    @patch("modules.comms.manager.build_meshtastic_client")
    def test_start_subscribes_to_bus_events(self, mock_build_client):
        """Test start subscribes to required bus events."""
        from modules.comms.manager import CommsManager

        mock_build_client.return_value = MagicMock()
        bus = MagicMock()
        config = {"modules": {"comms": {"simulated": True}}}
        manager = CommsManager(bus, config)

        manager.start()

        # Give thread time to start
        time.sleep(0.1)

        # Verify bus subscriptions
        subscribe_calls = [call[0][0] for call in bus.subscribe.call_args_list]
        assert "comms.send_message" in subscribe_calls
        assert "comms.request" in subscribe_calls
        assert "comms.get_status" in subscribe_calls
        assert "os.boot_complete" in subscribe_calls

        manager.stop()

    @patch("modules.comms.manager.build_meshtastic_client")
    def test_start_sets_running_flag(self, mock_build_client):
        """Test start sets running flag to True."""
        from modules.comms.manager import CommsManager

        mock_build_client.return_value = MagicMock()
        bus = MagicMock()
        config = {"modules": {"comms": {"simulated": True}}}
        manager = CommsManager(bus, config)

        manager.start()
        time.sleep(0.1)

        assert manager.running is True

        manager.stop()

    @patch("modules.comms.manager.build_meshtastic_client")
    def test_stop_sets_running_flag_false(self, mock_build_client):
        """Test stop sets running flag to False."""
        from modules.comms.manager import CommsManager

        mock_build_client.return_value = MagicMock()
        bus = MagicMock()
        config = {"modules": {"comms": {"simulated": True}}}
        manager = CommsManager(bus, config)

        manager.start()
        time.sleep(0.1)
        manager.stop()

        assert manager.running is False


class TestCommsManagerProcessRequest:
    """Tests for CommsManager request processing."""

    def test_process_request_missing_function_name(self):
        """Test _process_request handles missing function name."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)

        # Should not raise
        manager._process_request({"args": {}})

    def test_process_request_unknown_function(self):
        """Test _process_request handles unknown function."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.functions = {}

        # Should not raise
        manager._process_request({"function": "unknown_func"})

    def test_process_request_no_client(self):
        """Test _process_request handles no client."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.functions = {"test_func": lambda: None}
        manager.client = None

        # Should not raise
        manager._process_request({"function": "test_func"})

    def test_process_request_success(self):
        """Test _process_request publishes success response."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.client = MagicMock()
        manager.functions = {"test_func": MagicMock(return_value={"status": "ok"})}

        manager._process_request({"function": "test_func", "request_id": "req-1"})

        # Check that success response was published
        bus.publish.assert_called()
        call_args = bus.publish.call_args_list[-1]
        assert call_args[0][0] == "comms.response"
        assert call_args[0][1]["ok"] is True
        assert call_args[0][1]["request_id"] == "req-1"

    def test_process_request_error(self):
        """Test _process_request publishes error response on failure."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.client = MagicMock()
        manager.connected = True
        manager.functions = {"test_func": MagicMock(side_effect=Exception("Test error"))}

        manager._process_request({"function": "test_func", "request_id": "req-1"})

        # Check that error response was published
        bus.publish.assert_called()
        call_args = bus.publish.call_args_list[-1]
        assert call_args[0][0] == "comms.response"
        assert call_args[0][1]["ok"] is False
        assert "Test error" in call_args[0][1]["error"]


class TestCommsManagerDisconnection:
    """Tests for CommsManager disconnection handling."""

    def test_handle_disconnection_publishes_event(self):
        """Test _handle_disconnection publishes connection_lost event."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.connected = True
        manager._method_sequence = ["meshtastic"]
        manager._method_index = 0

        manager._handle_disconnection()

        assert manager.connected is False
        bus.publish.assert_any_call("comms.connection_lost", {"timestamp": pytest.approx(time.time(), abs=1)})

    def test_handle_disconnection_sets_fallback_index(self):
        """Test _handle_disconnection sets fallback start index."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        manager._method_index = 0

        manager._handle_disconnection()

        assert manager._fallback_start_index == 1


class TestCommsManagerPromotion:
    """Tests for CommsManager method promotion."""

    def test_should_promote_false_when_not_connected(self):
        """Test _should_promote returns False when not connected."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.connected = False

        assert manager._should_promote() is False

    def test_should_promote_false_when_already_preferred(self):
        """Test _should_promote returns False when already on preferred method."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        manager.method = "wifi"

        assert manager._should_promote() is False

    def test_should_promote_false_when_processing_request(self):
        """Test _should_promote returns False when processing a request."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.connected = True
        manager._method_sequence = ["wifi", "meshtastic"]
        manager.method = "meshtastic"
        manager._processing_request = True

        assert manager._should_promote() is False

    def test_meshtastic_outbox_empty_returns_true_for_non_meshtastic(self):
        """Test _meshtastic_outbox_empty returns True for non-meshtastic method."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.method = "wifi"

        assert manager._meshtastic_outbox_empty() is True

    def test_meshtastic_outbox_empty_checks_spool_depth(self):
        """Test _meshtastic_outbox_empty checks spool depth."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.method = "meshtastic"
        manager.client = MagicMock()
        manager.client.transport.spool.depth.return_value = 0

        assert manager._meshtastic_outbox_empty() is True

        manager.client.transport.spool.depth.return_value = 5

        assert manager._meshtastic_outbox_empty() is False


class TestCommsManagerPublishStatus:
    """Tests for CommsManager status publishing."""

    def test_publish_status_force(self):
        """Test _publish_status publishes when force=True."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True
        manager._last_status_key = ("wifi", True)

        manager._publish_status(force=True)

        bus.publish.assert_called_with("comms.status", pytest.approx(manager._build_status_payload(), abs=1))

    def test_publish_status_on_change(self):
        """Test _publish_status publishes on status change."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True
        manager._last_status_key = ("meshtastic", True)  # Different from current

        manager._publish_status()

        bus.publish.assert_called()

    def test_publish_status_skips_when_unchanged(self):
        """Test _publish_status skips when status unchanged and not forced."""
        from modules.comms.manager import CommsManager

        bus = MagicMock()
        config = {"modules": {"comms": {}}}
        manager = CommsManager(bus, config)
        manager.method = "wifi"
        manager.connected = True
        manager._last_status_key = ("wifi", True)

        manager._publish_status(force=False)

        bus.publish.assert_not_called()
