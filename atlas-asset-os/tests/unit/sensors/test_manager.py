import time
from framework.bus import MessageBus
from modules.sensors.manager import SensorsManager
from modules.sensors.workers.base import SensorWorker


def _base_config(sensors_cfg: dict) -> dict:
    return {
        "atlas": {"base_url": "http://localhost:8000", "api_token": None},
        "modules": {"sensors": sensors_cfg},
    }


class MockSensorWorker(SensorWorker):
    """Mock sensor worker for testing."""
    
    def __init__(self, bus, device_cfg, config):
        super().__init__(bus, device_cfg, config)
        self.run_called = False
        self.stop_called = False
    
    def run(self):
        self.run_called = True
        # Publish one sample output
        self.publish_output({"value": 42})
        # Then wait for stop
        while self._running:
            time.sleep(0.1)
    
    def stop(self):
        self.stop_called = True
        super().stop()


def test_sensors_manager_initialization():
    """Test that sensors manager initializes correctly."""
    config = _base_config({"enabled": True, "devices": []})
    bus = MessageBus()
    manager = SensorsManager(bus, config)
    
    assert manager.MODULE_NAME == "sensors"
    assert manager.MODULE_VERSION == "1.0.0"
    assert manager.DEPENDENCIES == []
    assert manager._devices == []
    assert manager._workers == {}


def test_sensors_manager_loads_devices_from_config():
    """Test that devices are loaded from configuration."""
    devices = [
        {"id": "sensor1", "type": "camera_bearing", "enabled": True},
        {"id": "sensor2", "type": "camera_bearing", "enabled": False},
    ]
    config = _base_config({"enabled": True, "devices": devices})
    bus = MessageBus()
    manager = SensorsManager(bus, config)
    
    assert len(manager._devices) == 2
    assert manager._devices[0]["id"] == "sensor1"
    assert manager._devices[1]["id"] == "sensor2"


def test_sensors_manager_handles_missing_devices():
    """Test that manager handles missing devices list gracefully."""
    config = _base_config({"enabled": True})
    bus = MessageBus()
    manager = SensorsManager(bus, config)
    
    assert manager._devices == []


def test_sensors_manager_handles_invalid_devices_config():
    """Test that manager handles invalid devices configuration."""
    config = _base_config({"enabled": True, "devices": "not-a-list"})
    bus = MessageBus()
    manager = SensorsManager(bus, config)
    
    assert manager._devices == []


def test_sensors_manager_starts_enabled_workers(monkeypatch):
    """Test that manager only starts enabled workers."""
    from modules.sensors import workers
    
    # Temporarily add mock worker to registry
    original_registry = workers.WORKER_REGISTRY.copy()
    workers.WORKER_REGISTRY["mock_sensor"] = MockSensorWorker
    
    try:
        devices = [
            {"id": "sensor1", "type": "mock_sensor", "enabled": True},
            {"id": "sensor2", "type": "mock_sensor", "enabled": False},
            {"id": "sensor3", "type": "mock_sensor"},  # enabled by default
        ]
        config = _base_config({"enabled": True, "devices": devices})
        bus = MessageBus()
        manager = SensorsManager(bus, config)
        
        manager.start()
        time.sleep(0.2)  # Let workers start
        
        # Should have started sensor1 and sensor3, but not sensor2
        assert "sensor1" in manager._workers
        assert "sensor2" not in manager._workers
        assert "sensor3" in manager._workers
        
        # Verify workers actually ran
        assert manager._workers["sensor1"].run_called
        assert manager._workers["sensor3"].run_called
        
        manager.stop()
    finally:
        # Restore original registry
        workers.WORKER_REGISTRY = original_registry


def test_sensors_manager_skips_invalid_device_configs(monkeypatch):
    """Test that manager skips invalid device configurations."""
    from modules.sensors import workers
    
    original_registry = workers.WORKER_REGISTRY.copy()
    workers.WORKER_REGISTRY["mock_sensor"] = MockSensorWorker
    
    try:
        devices = [
            "not-a-dict",
            {"type": "mock_sensor"},  # missing id
            {"id": "sensor2"},  # missing type
            {"id": "sensor3", "type": "mock_sensor", "enabled": True},  # valid
        ]
        config = _base_config({"enabled": True, "devices": devices})
        bus = MessageBus()
        manager = SensorsManager(bus, config)
        
        manager.start()
        time.sleep(0.2)
        
        # Should only have started sensor3
        assert len(manager._workers) == 1
        assert "sensor3" in manager._workers
        
        manager.stop()
    finally:
        workers.WORKER_REGISTRY = original_registry


def test_sensors_manager_handles_unknown_sensor_type():
    """Test that manager handles unknown sensor types gracefully."""
    devices = [
        {"id": "sensor1", "type": "unknown_type", "enabled": True},
    ]
    config = _base_config({"enabled": True, "devices": devices})
    bus = MessageBus()
    manager = SensorsManager(bus, config)
    
    manager.start()
    time.sleep(0.1)
    
    # Should not have started any workers
    assert len(manager._workers) == 0
    
    manager.stop()


def test_sensors_manager_stops_all_workers(monkeypatch):
    """Test that manager stops all workers on stop."""
    from modules.sensors import workers
    
    original_registry = workers.WORKER_REGISTRY.copy()
    workers.WORKER_REGISTRY["mock_sensor"] = MockSensorWorker
    
    try:
        devices = [
            {"id": "sensor1", "type": "mock_sensor", "enabled": True},
            {"id": "sensor2", "type": "mock_sensor", "enabled": True},
        ]
        config = _base_config({"enabled": True, "devices": devices})
        bus = MessageBus()
        manager = SensorsManager(bus, config)
        
        manager.start()
        time.sleep(0.2)
        
        # Verify workers are running
        assert manager._workers["sensor1"]._running
        assert manager._workers["sensor2"]._running
        
        # Keep references to workers before stop clears them
        worker1 = manager._workers["sensor1"]
        worker2 = manager._workers["sensor2"]
        
        # Stop manager
        manager.stop()
        time.sleep(0.1)
        
        # Verify all workers were stopped
        assert worker1.stop_called
        assert worker2.stop_called
        assert not worker1._running
        assert not worker2._running
        
        # Workers should be cleared from manager
        assert len(manager._workers) == 0
    finally:
        workers.WORKER_REGISTRY = original_registry


def test_sensor_worker_publishes_output():
    """Test that sensor worker can publish output to bus."""
    bus = MessageBus()
    outputs = []
    
    def capture_output(data):
        outputs.append(data)
    
    bus.subscribe("sensor.output", capture_output)
    
    device_cfg = {"id": "test-sensor", "type": "test"}
    worker = SensorWorker(bus, device_cfg, {})
    
    worker.publish_output({"reading": 123})
    
    assert len(outputs) == 1
    assert outputs[0]["sensor_id"] == "test-sensor"
    assert outputs[0]["sensor_type"] == "test"
    assert outputs[0]["data"]["reading"] == 123
    assert "timestamp" in outputs[0]


def test_sensor_worker_lifecycle():
    """Test sensor worker start and stop lifecycle."""
    bus = MessageBus()
    device_cfg = {"id": "test-sensor", "type": "test"}
    worker = SensorWorker(bus, device_cfg, {})
    
    # Initially not running
    assert worker._running is False
    assert worker._thread is None
    
    # Start worker
    worker.start()
    time.sleep(0.1)
    
    assert worker._running is True
    assert worker._thread is not None
    assert worker._thread.is_alive()
    
    # Stop worker
    worker.stop()
    time.sleep(0.1)
    
    assert worker._running is False
    assert not worker._thread.is_alive()


def test_sensor_worker_prevents_double_start():
    """Test that worker prevents starting twice."""
    bus = MessageBus()
    device_cfg = {"id": "test-sensor", "type": "test"}
    worker = SensorWorker(bus, device_cfg, {})
    
    worker.start()
    time.sleep(0.1)
    first_thread = worker._thread
    
    # Try to start again
    worker.start()
    time.sleep(0.1)
    
    # Should still have the same thread
    assert worker._thread is first_thread
    
    worker.stop()
