"""Integration test for OS boot sequence.

Tests the full OS boot sequence end-to-end.
This is an integration test that verifies the complete boot process.
"""

import sys
import time
import threading
from pathlib import Path

import pytest

# Paths are set up by conftest.py, but ensure we have them here too
_ASSET_OS_ROOT = Path(__file__).resolve().parents[2]

# Add ATLAS_ASSET_OS root to path so we can import framework and modules
_ASSET_OS_ROOT_STR = str(_ASSET_OS_ROOT.resolve())
if _ASSET_OS_ROOT_STR not in sys.path:
    sys.path.insert(0, _ASSET_OS_ROOT_STR)

# Import after path setup
from framework.master import OSManager  # noqa: E402

# Hardcoded test config - no external file needed
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
        "comms": {
            "enabled": True,
            "simulated": True,
            "gateway_node_id": "!test123",
            "enabled_methods": ["meshtastic"],
        },
        "operations": {"enabled": True},
    },
}


class TestOSBoot:
    """Integration test for full OS boot sequence."""

    @pytest.fixture
    def os_manager(self):
        """Create OS manager with test config."""
        return OSManager(config=TEST_CONFIG)

    def test_os_boot_sequence(self, os_manager):
        """Test full OS boot sequence end-to-end."""
        boot_complete = threading.Event()
        boot_data = {}
        thread_errors: list[BaseException] = []

        def on_boot_complete(data):
            boot_data.update(data)
            boot_complete.set()

        os_manager.bus.subscribe("os.boot_complete", on_boot_complete)

        # Start OS in a thread
        def run_os():
            try:
                os_manager._start_modules()
                os_manager.bus.publish("os.boot_complete", {"ts": time.time()})
                # Run briefly
                time.sleep(0.1)
            except (Exception, SystemExit) as exc:
                thread_errors.append(exc)
            finally:
                try:
                    os_manager.shutdown()
                except SystemExit:
                    # OSManager.shutdown() may raise SystemExit when stopping the process/event loop;
                    # this is expected in tests and is intentionally ignored.
                    pass

        boot_thread = threading.Thread(target=run_os, daemon=True)
        boot_thread.start()

        # Wait for boot complete signal
        assert boot_complete.wait(timeout=5.0), "Boot did not complete in time"
        assert "ts" in boot_data

        # Verify modules are running
        assert os_manager.module_loader.get_module("comms") is not None
        assert os_manager.module_loader.get_module("operations") is not None

        # Verify modules are actually running
        comms_module = os_manager.module_loader.get_module("comms")
        operations_module = os_manager.module_loader.get_module("operations")
        assert comms_module.running is True
        assert operations_module.running is True

        boot_thread.join(timeout=5.0)
        if boot_thread.is_alive():
            raise AssertionError("OS boot thread did not finish within timeout")
        if thread_errors:
            raise RuntimeError("OS boot thread failed") from thread_errors[0]
