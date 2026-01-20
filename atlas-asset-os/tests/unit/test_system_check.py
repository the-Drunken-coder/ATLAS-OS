"""Unit tests for system check functionality."""

import time
from framework.bus import MessageBus
from framework.master import OSManager
from modules.module_base import ModuleBase


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
        "data_store": {"enabled": True},
        "sensors": {"enabled": True, "devices": []},
    },
}


def test_module_base_system_check():
    """Test default system_check implementation in ModuleBase."""
    bus = MessageBus()

    class TestModule(ModuleBase):
        MODULE_NAME = "test_module"
        MODULE_VERSION = "1.0.0"

        def start(self):
            self.running = True

        def stop(self):
            self.running = False

    module = TestModule(bus, {})

    # Module not running
    result = module.system_check()
    assert isinstance(result, dict)
    assert "healthy" in result
    assert result["healthy"] is False
    assert result["status"] == "stopped"

    # Module running
    module.start()
    result = module.system_check()
    assert result["healthy"] is True
    assert result["status"] == "running"

    # Module stopped
    module.stop()
    result = module.system_check()
    assert result["healthy"] is False


def test_module_loader_system_check():
    """Test module loader run_system_check method."""
    os_manager = OSManager(config=TEST_CONFIG)

    # Discover and load modules
    os_manager.module_loader.discover_modules()
    os_manager.module_loader.resolve_dependencies()
    os_manager.module_loader.load_modules()
    os_manager.module_loader.start_modules()

    # Give modules time to start
    time.sleep(0.2)

    # Run system check
    results = os_manager.module_loader.run_system_check(timeout_s=5.0)

    assert isinstance(results, dict)
    assert "overall_healthy" in results
    assert "modules" in results
    assert isinstance(results["modules"], dict)

    # Check that all enabled modules are in results
    for module_name in ["comms", "operations", "data_store", "sensors"]:
        assert module_name in results["modules"]
        module_result = results["modules"][module_name]
        assert isinstance(module_result, dict)
        assert "healthy" in module_result
        assert isinstance(module_result["healthy"], bool)

    # Clean up
    os_manager.module_loader.stop_modules()


def test_system_check_request_response():
    """Test system check request/response via bus."""
    os_manager = OSManager(config=TEST_CONFIG)

    # Discover and load modules
    os_manager.module_loader.discover_modules()
    os_manager.module_loader.resolve_dependencies()
    os_manager.module_loader.load_modules()
    os_manager.module_loader.start_modules()

    # Give modules time to start
    time.sleep(0.2)

    # Set up listener for response
    response_received = {"data": None}

    def _handle_response(data):
        response_received["data"] = data

    os_manager.bus.subscribe("system.check.response", _handle_response)

    # Trigger system check via operations
    os_manager.bus.publish("system.check.request", {"request_id": "test-123"})

    # Wait for response
    time.sleep(0.5)

    # Verify response
    assert response_received["data"] is not None
    data = response_received["data"]
    assert isinstance(data, dict)
    assert "results" in data
    assert "timestamp" in data
    assert "request_id" in data
    assert data["request_id"] == "test-123"

    # Verify results structure
    results = data["results"]
    assert "overall_healthy" in results
    assert "modules" in results

    # Clean up
    os_manager.module_loader.stop_modules()


def test_system_check_timeout_handling():
    """Test that slow system checks are treated as unhealthy."""
    bus = MessageBus()

    class SlowModule(ModuleBase):
        MODULE_NAME = "slow_module"
        MODULE_VERSION = "1.0.0"

        def start(self):
            self.running = True

        def stop(self):
            self.running = False

        def system_check(self):
            # Simulate slow check
            time.sleep(2)
            return {"healthy": True, "status": "running"}

    config = {
        "modules": {"slow_module": {"enabled": True}},
    }

    # Create module loader with custom module
    from modules.module_loader import ModuleLoader

    loader = ModuleLoader(bus, config, modules_dirs=[])
    loader._module_classes = {"slow_module": SlowModule}
    loader._load_order = ["slow_module"]
    loader.load_modules()
    loader.start_modules()

    # Run check with short timeout
    results = loader.run_system_check(timeout_s=0.5)

    assert results["overall_healthy"] is False
    assert "slow_module" in results["modules"]
    assert results["modules"]["slow_module"]["healthy"] is False
    assert results["modules"]["slow_module"]["status"] == "timeout"

    # Clean up
    loader.stop_modules()


def test_operations_system_check():
    """Test operations module system_check implementation."""
    bus = MessageBus()
    config = {
        "atlas": {
            "base_url": "http://localhost:8000",
            "asset": {"id": "test-001"},
        },
        "modules": {
            "operations": {
                "enabled": True,
                "heartbeat_interval_s": 30.0,
                "checkin_interval_s": 30.0,
            }
        },
    }

    from modules.operations.manager import OperationsManager

    manager = OperationsManager(bus, config)
    manager.start()

    # Give it time to start
    time.sleep(0.1)

    result = manager.system_check()

    assert isinstance(result, dict)
    assert "healthy" in result
    assert "status" in result
    assert result["healthy"] is True
    assert "heartbeat_interval_s" in result
    assert "checkin_interval_s" in result
    assert "registration_complete" in result

    manager.stop()


def test_comms_system_check():
    """Test comms module system_check implementation."""
    bus = MessageBus()
    config = {
        "modules": {
            "comms": {
                "enabled": True,
                "simulated": True,
                "gateway_node_id": "!test",
            }
        }
    }

    from modules.comms.manager import CommsManager

    manager = CommsManager(bus, config)
    manager.start()

    # Give it time to start
    time.sleep(0.1)

    result = manager.system_check()

    assert isinstance(result, dict)
    assert "healthy" in result
    assert "status" in result
    assert "method" in result
    assert "simulated" in result
    assert result["simulated"] is True

    manager.stop()


def test_sensors_system_check():
    """Test sensors module system_check implementation."""
    bus = MessageBus()
    config = {
        "modules": {
            "sensors": {
                "enabled": True,
                "devices": [],
            }
        }
    }

    from modules.sensors.manager import SensorsManager

    manager = SensorsManager(bus, config)
    manager.start()

    result = manager.system_check()

    assert isinstance(result, dict)
    assert "healthy" in result
    assert "status" in result
    assert "worker_count" in result
    assert result["worker_count"] == 0

    manager.stop()


def test_data_store_system_check():
    """Test data_store module system_check implementation."""
    bus = MessageBus()
    config = {
        "modules": {
            "data_store": {
                "enabled": True,
            }
        }
    }

    from modules.data_store.manager import DataStoreManager

    manager = DataStoreManager(bus, config)
    manager.start()

    result = manager.system_check()

    assert isinstance(result, dict)
    assert "healthy" in result
    assert "status" in result
    assert "namespaces" in result
    assert "total_records" in result
    assert "persistence_enabled" in result

    manager.stop()
