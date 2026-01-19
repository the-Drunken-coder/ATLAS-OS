"""Unit tests for OSManager."""

import sys
from pathlib import Path

import pytest

# Paths should be set up by conftest.py, but ensure we have them here too
_ASSET_OS_ROOT = Path(__file__).resolve().parents[2]

# Add ATLAS_ASSET_OS root to path so we can import framework and modules
_ASSET_OS_ROOT_STR = str(_ASSET_OS_ROOT.resolve())
if _ASSET_OS_ROOT_STR not in sys.path:
    sys.path.insert(0, _ASSET_OS_ROOT_STR)

from framework.master import OSManager  # noqa: E402

# Hardcoded test config
TEST_CONFIG = {
    "atlas": {
        "base_url": "http://localhost:8000",
        "api_token": None,
        "asset": {
            "id": "test-asset-001",
            "name": "Test Asset",
            "model_id": "test-asset",
        },
    },
    "modules": {
        "comms": {"enabled": True, "simulated": True, "gateway_node_id": "!test123"},
        "operations": {"enabled": True},
    },
}


class TestOSManager:
    """Unit tests for OSManager."""

    @pytest.fixture
    def os_manager(self):
        """Create OS manager with test config."""
        return OSManager(config=TEST_CONFIG)

    def test_config_loads(self, os_manager):
        """Test that config file loads correctly."""
        assert os_manager.config is not None
        assert "atlas" in os_manager.config
        assert "modules" in os_manager.config
        assert os_manager.config["atlas"]["asset"]["id"] == "test-asset-001"

    def test_bus_created(self, os_manager):
        """Test that message bus is created."""
        assert os_manager.bus is not None

    def test_module_loader_created(self, os_manager):
        """Test that module loader is created."""
        assert os_manager.module_loader is not None

    def test_running_state(self, os_manager):
        """Test initial running state."""
        assert os_manager.running is True

    def test_shutdown(self, os_manager):
        """Test shutdown method."""
        # shutdown() should NOT call sys.exit(0) when running under pytest
        # to avoid "Exception ignored in thread" warnings during test cleanup
        os_manager.shutdown()
        assert os_manager.running is False
