"""Tests for the WiFi transport bridge."""

from unittest.mock import MagicMock, Mock, patch

import pytest


class TestWifiBridgeHelpers:
    """Tests for WiFi bridge helper functions."""

    def test_get_current_ssid_windows(self):
        """Test get_current_ssid on Windows."""
        from modules.comms.transports.wifi.bridge import _current_ssid_windows

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="    SSID                   : TestNetwork\n    BSSID                  : 00:11:22:33:44:55\n"
            )

            result = _current_ssid_windows()

            assert result == "TestNetwork"

    def test_get_current_ssid_windows_not_connected(self):
        """Test get_current_ssid on Windows when not connected."""
        from modules.comms.transports.wifi.bridge import _current_ssid_windows

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")

            result = _current_ssid_windows()

            assert result is None

    def test_get_current_ssid_linux(self):
        """Test get_current_ssid on Linux."""
        from modules.comms.transports.wifi.bridge import _current_ssid_linux

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="yes:TestNetwork\nno:OtherNetwork\n"
            )

            result = _current_ssid_linux()

            assert result == "TestNetwork"

    def test_get_current_ssid_linux_not_connected(self):
        """Test get_current_ssid on Linux when not connected."""
        from modules.comms.transports.wifi.bridge import _current_ssid_linux

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="no:Network1\nno:Network2\n"
            )

            result = _current_ssid_linux()

            assert result is None

    def test_get_current_ssid_macos(self):
        """Test get_current_ssid on macOS."""
        from modules.comms.transports.wifi.bridge import _current_ssid_macos

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Current Wi-Fi Network: TestNetwork"
            )

            result = _current_ssid_macos("en0")

            assert result == "TestNetwork"
            mock_run.assert_called_once()

    def test_get_current_ssid_macos_no_interface(self):
        """Test get_current_ssid on macOS with no interface."""
        from modules.comms.transports.wifi.bridge import _current_ssid_macos

        result = _current_ssid_macos(None)

        assert result is None

    def test_get_current_ssid_macos_not_connected(self):
        """Test get_current_ssid on macOS when not connected."""
        from modules.comms.transports.wifi.bridge import _current_ssid_macos

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")

            result = _current_ssid_macos("en0")

            assert result is None


class TestWifiBridgeBadSSID:
    """Tests for bad SSID tracking."""

    def test_mark_bad_ssid(self):
        """Test marking an SSID as bad."""
        from modules.comms.transports.wifi.bridge import mark_bad_ssid, is_bad_ssid, BAD_SSIDS

        # Clear any existing bad SSIDs
        BAD_SSIDS.clear()

        mark_bad_ssid("BadNetwork")

        assert is_bad_ssid("BadNetwork") is True
        assert is_bad_ssid("GoodNetwork") is False

    def test_mark_bad_ssid_none(self):
        """Test marking None as bad SSID does nothing."""
        from modules.comms.transports.wifi.bridge import mark_bad_ssid, BAD_SSIDS

        initial_count = len(BAD_SSIDS)

        mark_bad_ssid(None)

        assert len(BAD_SSIDS) == initial_count


class TestWifiConnect:
    """Tests for WiFi connection functions."""

    def test_connect_with_windows_success(self):
        """Test successful WiFi connection on Windows."""
        from modules.comms.transports.wifi.bridge import _connect_with_windows

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = _connect_with_windows("TestNetwork", "wlan0")

            assert result is True
            mock_run.assert_called_once()

    def test_connect_with_windows_failure(self):
        """Test failed WiFi connection on Windows."""
        from modules.comms.transports.wifi.bridge import _connect_with_windows

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Connection failed", stdout="")

            result = _connect_with_windows("TestNetwork", None)

            assert result is False

    def test_connect_with_nmcli_success_no_password(self):
        """Test successful WiFi connection via nmcli without password."""
        from modules.comms.transports.wifi.bridge import _connect_with_nmcli

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = _connect_with_nmcli("OpenNetwork", None)

            assert result is True

    def test_connect_with_nmcli_success_with_password(self):
        """Test successful WiFi connection via nmcli with password."""
        from modules.comms.transports.wifi.bridge import _connect_with_nmcli

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = _connect_with_nmcli("SecureNetwork", "password123")

            assert result is True

    def test_connect_with_nmcli_failure(self):
        """Test failed WiFi connection via nmcli."""
        from modules.comms.transports.wifi.bridge import _connect_with_nmcli

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Network not found", stdout="")

            result = _connect_with_nmcli("NonExistentNetwork", None)

            assert result is False

    def test_connect_with_networksetup_no_interface(self):
        """Test networksetup connection with no interface."""
        from modules.comms.transports.wifi.bridge import _connect_with_networksetup

        result = _connect_with_networksetup("TestNetwork", None, None)

        assert result is False

    def test_connect_with_networksetup_success(self):
        """Test successful networksetup connection."""
        from modules.comms.transports.wifi.bridge import _connect_with_networksetup

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = _connect_with_networksetup("TestNetwork", "password", "en0")

            assert result is True


class TestWifiDisconnect:
    """Tests for WiFi disconnection functions."""

    def test_disconnect_windows(self):
        """Test WiFi disconnection on Windows."""
        from modules.comms.transports.wifi.bridge import _disconnect_windows

        with patch("subprocess.run") as mock_run:
            _disconnect_windows()

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "netsh" in args
            assert "disconnect" in args

    def test_disconnect_linux(self):
        """Test WiFi disconnection on Linux."""
        from modules.comms.transports.wifi.bridge import _disconnect_linux

        with patch("subprocess.run") as mock_run:
            _disconnect_linux("wlan0")

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "nmcli" in args
            assert "disconnect" in args

    def test_disconnect_macos_no_interface(self):
        """Test WiFi disconnection on macOS with no interface."""
        from modules.comms.transports.wifi.bridge import _disconnect_macos

        with patch("subprocess.run") as mock_run:
            _disconnect_macos(None)

            mock_run.assert_not_called()


class TestScanOpenNetworks:
    """Tests for scanning open networks."""

    def test_scan_open_networks_linux(self):
        """Test scanning for open networks on Linux."""
        from modules.comms.transports.wifi.bridge import _scan_open_networks_linux

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="OpenNetwork:\nSecureNetwork:WPA2\nAnotherOpen:--\n"
            )

            result = _scan_open_networks_linux()

            assert "OpenNetwork" in result
            assert "AnotherOpen" in result
            assert "SecureNetwork" not in result

    def test_scan_open_networks_linux_failure(self):
        """Test scanning for open networks on Linux when nmcli fails."""
        from modules.comms.transports.wifi.bridge import _scan_open_networks_linux

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")

            result = _scan_open_networks_linux()

            assert result == []


class TestWifiApiClient:
    """Tests for the WifiApiClient class."""

    def test_wifi_api_client_init(self):
        """Test WifiApiClient initialization."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token="test-token", timeout=30.0)

        assert client._base_url == "http://localhost:8000"
        assert client._token == "test-token"
        assert client._timeout == 30.0

    def test_wifi_api_client_strips_trailing_slash(self):
        """Test WifiApiClient strips trailing slash from base_url."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000/", token=None, timeout=10.0)

        assert client._base_url == "http://localhost:8000"

    def test_wifi_api_client_test_echo(self):
        """Test WifiApiClient.test_echo method."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)

        result = client.test_echo("hello")

        assert result == {"echo": "hello"}

    def test_wifi_api_client_test_echo_default(self):
        """Test WifiApiClient.test_echo with default message."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)

        result = client.test_echo()

        assert result == {"echo": "ping"}

    def test_wifi_api_client_is_connected(self):
        """Test WifiApiClient.is_connected method."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)

        with patch("modules.comms.transports.wifi.bridge.get_current_ssid") as mock_get_ssid:
            mock_get_ssid.return_value = "TestNetwork"

            result = client.is_connected("wlan0")

            assert result is True
            mock_get_ssid.assert_called_once_with("wlan0")

    def test_wifi_api_client_is_connected_false(self):
        """Test WifiApiClient.is_connected returns False when not connected."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)

        with patch("modules.comms.transports.wifi.bridge.get_current_ssid") as mock_get_ssid:
            mock_get_ssid.return_value = None

            result = client.is_connected("wlan0")

            assert result is False

    def test_wifi_api_client_current_ssid(self):
        """Test WifiApiClient.current_ssid method."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)

        with patch("modules.comms.transports.wifi.bridge.get_current_ssid") as mock_get_ssid:
            mock_get_ssid.return_value = "MyNetwork"

            result = client.current_ssid("wlan0")

            assert result == "MyNetwork"

    def test_wifi_api_client_mark_bad_current(self):
        """Test WifiApiClient.mark_bad_current method."""
        from modules.comms.transports.wifi.bridge import WifiApiClient, BAD_SSIDS

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)
        BAD_SSIDS.clear()

        with patch("modules.comms.transports.wifi.bridge.get_current_ssid") as mock_get_ssid:
            mock_get_ssid.return_value = "BadNetwork"

            client.mark_bad_current("wlan0")

            assert "BadNetwork" in BAD_SSIDS

    def test_wifi_api_client_disconnect(self):
        """Test WifiApiClient.disconnect method."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)

        with patch("modules.comms.transports.wifi.bridge.disconnect_current") as mock_disconnect:
            client.disconnect("wlan0")

            mock_disconnect.assert_called_once_with("wlan0")

    def test_wifi_api_client_getattr_direct_methods(self):
        """Test WifiApiClient __getattr__ for direct methods."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)

        # list_entities should be a valid method
        method = getattr(client, "list_entities", None)
        assert method is not None
        assert callable(method)

    def test_wifi_api_client_getattr_unknown_method(self):
        """Test WifiApiClient __getattr__ raises for unknown methods."""
        from modules.comms.transports.wifi.bridge import WifiApiClient

        client = WifiApiClient("http://localhost:8000", token=None, timeout=10.0)

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = client.unknown_method


class TestBuildWifiClient:
    """Tests for build_wifi_client function."""

    def test_build_wifi_client_missing_base_url(self):
        """Test build_wifi_client raises when base_url is missing."""
        from modules.comms.transports.wifi.bridge import build_wifi_client

        with patch("modules.comms.transports.wifi.bridge.AtlasCommandHttpClient", MagicMock()):
            with pytest.raises(RuntimeError, match="base_url is required"):
                build_wifi_client(base_url="", api_token=None, wifi_config={})

    def test_build_wifi_client_missing_http_client(self):
        """Test build_wifi_client raises when AtlasCommandHttpClient is not available."""
        from modules.comms.transports.wifi import bridge

        original = bridge.AtlasCommandHttpClient
        bridge.AtlasCommandHttpClient = None

        try:
            with pytest.raises(RuntimeError, match="atlas_asset_http_client_python is required"):
                bridge.build_wifi_client(
                    base_url="http://localhost:8000",
                    api_token=None,
                    wifi_config={},
                )
        finally:
            bridge.AtlasCommandHttpClient = original

    def test_build_wifi_client_test_mode_skips_connect(self):
        """Test build_wifi_client skips connection in test mode."""
        from modules.comms.transports.wifi.bridge import build_wifi_client, WifiApiClient

        with patch("modules.comms.transports.wifi.bridge.AtlasCommandHttpClient", MagicMock()):
            with patch("modules.comms.transports.wifi.bridge._is_test_env", return_value=True):
                result = build_wifi_client(
                    base_url="http://localhost:8000",
                    api_token="token",
                    wifi_config={"timeout_s": 15.0},
                )

                assert isinstance(result, WifiApiClient)


class TestVerifyConnectivity:
    """Tests for connectivity verification."""

    def test_verify_connectivity_success(self):
        """Test _verify_connectivity returns True on success."""
        from modules.comms.transports.wifi import bridge

        # Mock httpx
        mock_httpx = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response
        original_httpx = bridge.httpx
        bridge.httpx = mock_httpx

        try:
            result = bridge._verify_connectivity("http://localhost:8000", 5.0)
            assert result is True
        finally:
            bridge.httpx = original_httpx

    def test_verify_connectivity_failure(self):
        """Test _verify_connectivity returns False on failure."""
        from modules.comms.transports.wifi import bridge

        # Mock httpx to raise exception
        mock_httpx = MagicMock()
        mock_httpx.get.side_effect = Exception("Connection failed")
        original_httpx = bridge.httpx
        bridge.httpx = mock_httpx

        try:
            result = bridge._verify_connectivity("http://localhost:8000", 5.0)
            assert result is False
        finally:
            bridge.httpx = original_httpx

    def test_verify_connectivity_no_httpx(self):
        """Test _verify_connectivity returns False when httpx not available."""
        from modules.comms.transports.wifi import bridge

        original_httpx = bridge.httpx
        bridge.httpx = None

        try:
            result = bridge._verify_connectivity("http://localhost:8000", 5.0)
            assert result is False
        finally:
            bridge.httpx = original_httpx
