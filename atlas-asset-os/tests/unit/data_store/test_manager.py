import time
import tempfile
from pathlib import Path
from framework.bus import MessageBus
from modules.data_store.manager import DataStoreManager


def _base_config(data_store_cfg: dict) -> dict:
    return {
        "atlas": {"base_url": "http://localhost:8000", "api_token": None},
        "modules": {"data_store": data_store_cfg},
    }


def test_data_store_initialization():
    """Test that data store manager initializes correctly."""
    config = _base_config({"enabled": True})
    bus = MessageBus()
    manager = DataStoreManager(bus, config)
    
    assert manager.MODULE_NAME == "data_store"
    assert manager.MODULE_VERSION == "1.0.0"
    assert manager.DEPENDENCIES == []
    assert manager._store == {}
    assert manager._persist_enabled is False


def test_data_store_put_and_get():
    """Test basic put and get operations."""
    config = _base_config({"enabled": True})
    bus = MessageBus()
    manager = DataStoreManager(bus, config)
    manager.start()
    
    # Track published events
    updated_events = []
    response_events = []
    
    def on_updated(data):
        updated_events.append(data)
    
    def on_response(data):
        response_events.append(data)
    
    bus.subscribe("data_store.updated", on_updated)
    bus.subscribe("data_store.response", on_response)
    
    # Put a value
    bus.publish("data_store.put", {
        "namespace": "test",
        "key": "foo",
        "value": {"bar": "baz"},
        "meta": {"source": "test"}
    })
    
    time.sleep(0.1)
    
    # Verify updated event was published
    assert len(updated_events) == 1
    assert updated_events[0]["namespace"] == "test"
    assert updated_events[0]["key"] == "foo"
    assert updated_events[0]["record"]["value"] == {"bar": "baz"}
    assert updated_events[0]["record"]["meta"] == {"source": "test"}
    assert "updated_at" in updated_events[0]["record"]
    
    # Get the value
    bus.publish("data_store.get", {
        "namespace": "test",
        "key": "foo",
        "request_id": "req-1"
    })
    
    time.sleep(0.1)
    
    # Verify response was published
    assert len(response_events) == 1
    assert response_events[0]["namespace"] == "test"
    assert response_events[0]["key"] == "foo"
    assert response_events[0]["record"]["value"] == {"bar": "baz"}
    assert response_events[0]["request_id"] == "req-1"
    
    manager.stop()


def test_data_store_delete():
    """Test delete operation."""
    config = _base_config({"enabled": True})
    bus = MessageBus()
    manager = DataStoreManager(bus, config)
    manager.start()
    
    deleted_events = []
    
    def on_deleted(data):
        deleted_events.append(data)
    
    bus.subscribe("data_store.deleted", on_deleted)
    
    # Put a value
    bus.publish("data_store.put", {
        "namespace": "test",
        "key": "foo",
        "value": 123
    })
    
    time.sleep(0.1)
    
    # Delete it
    bus.publish("data_store.delete", {
        "namespace": "test",
        "key": "foo"
    })
    
    time.sleep(0.1)
    
    # Verify deleted event
    assert len(deleted_events) == 1
    assert deleted_events[0]["namespace"] == "test"
    assert deleted_events[0]["key"] == "foo"
    assert deleted_events[0]["record"]["value"] == 123
    
    # Try to get the deleted value
    response_events = []
    bus.subscribe("data_store.response", lambda d: response_events.append(d))
    
    bus.publish("data_store.get", {
        "namespace": "test",
        "key": "foo"
    })
    
    time.sleep(0.1)
    
    # Should return None
    assert len(response_events) == 1
    assert response_events[0]["record"] is None
    
    manager.stop()


def test_data_store_list():
    """Test list operation."""
    config = _base_config({"enabled": True})
    bus = MessageBus()
    manager = DataStoreManager(bus, config)
    manager.start()
    
    response_events = []
    bus.subscribe("data_store.response", lambda d: response_events.append(d))
    
    # Put multiple values
    bus.publish("data_store.put", {"namespace": "test", "key": "a", "value": 1})
    bus.publish("data_store.put", {"namespace": "test", "key": "b", "value": 2})
    bus.publish("data_store.put", {"namespace": "test", "key": "c", "value": 3})
    
    time.sleep(0.1)
    
    # List keys
    bus.publish("data_store.list", {
        "namespace": "test",
        "request_id": "list-1"
    })
    
    time.sleep(0.1)
    
    # Verify response
    assert len(response_events) == 1
    assert response_events[0]["namespace"] == "test"
    assert set(response_events[0]["keys"]) == {"a", "b", "c"}
    assert response_events[0]["request_id"] == "list-1"
    
    manager.stop()


def test_data_store_snapshot():
    """Test snapshot operation."""
    config = _base_config({"enabled": True})
    bus = MessageBus()
    manager = DataStoreManager(bus, config)
    manager.start()
    
    snapshot_events = []
    bus.subscribe("data_store.snapshot", lambda d: snapshot_events.append(d))
    
    # Put values in multiple namespaces
    bus.publish("data_store.put", {"namespace": "ns1", "key": "a", "value": 1})
    bus.publish("data_store.put", {"namespace": "ns1", "key": "b", "value": 2})
    bus.publish("data_store.put", {"namespace": "ns2", "key": "x", "value": 10})
    
    time.sleep(0.1)
    
    # Request full snapshot
    bus.publish("data_store.snapshot.request", {"request_id": "snap-1"})
    
    time.sleep(0.1)
    
    # Verify snapshot
    assert len(snapshot_events) == 1
    assert "ns1" in snapshot_events[0]["snapshot"]
    assert "ns2" in snapshot_events[0]["snapshot"]
    assert "a" in snapshot_events[0]["snapshot"]["ns1"]
    assert "b" in snapshot_events[0]["snapshot"]["ns1"]
    assert "x" in snapshot_events[0]["snapshot"]["ns2"]
    assert snapshot_events[0]["request_id"] == "snap-1"
    
    # Request namespace-specific snapshot
    snapshot_events.clear()
    bus.publish("data_store.snapshot.request", {
        "namespace": "ns1",
        "request_id": "snap-2"
    })
    
    time.sleep(0.1)
    
    # Verify namespace snapshot
    assert len(snapshot_events) == 1
    assert "ns1" in snapshot_events[0]["snapshot"]
    assert "ns2" not in snapshot_events[0]["snapshot"]
    assert snapshot_events[0]["request_id"] == "snap-2"
    
    manager.stop()


def test_data_store_namespace_isolation():
    """Test that namespaces are isolated from each other."""
    config = _base_config({"enabled": True})
    bus = MessageBus()
    manager = DataStoreManager(bus, config)
    manager.start()
    
    response_events = []
    bus.subscribe("data_store.response", lambda d: response_events.append(d))
    
    # Put same key in different namespaces
    bus.publish("data_store.put", {"namespace": "ns1", "key": "foo", "value": "value1"})
    bus.publish("data_store.put", {"namespace": "ns2", "key": "foo", "value": "value2"})
    
    time.sleep(0.1)
    
    # Get from ns1
    bus.publish("data_store.get", {"namespace": "ns1", "key": "foo"})
    time.sleep(0.1)
    
    assert response_events[0]["record"]["value"] == "value1"
    
    # Get from ns2
    response_events.clear()
    bus.publish("data_store.get", {"namespace": "ns2", "key": "foo"})
    time.sleep(0.1)
    
    assert response_events[0]["record"]["value"] == "value2"
    
    manager.stop()


def test_data_store_persistence():
    """Test persistence loading and saving."""
    with tempfile.TemporaryDirectory() as tmpdir:
        persist_path = Path(tmpdir) / "store.json"
        
        config = _base_config({
            "enabled": True,
            "persistence": {
                "enabled": True,
                "path": str(persist_path),
                "persist_on_change": True
            }
        })
        
        bus = MessageBus()
        manager = DataStoreManager(bus, config)
        manager.start()
        
        # Put some values
        bus.publish("data_store.put", {"namespace": "test", "key": "a", "value": 1})
        bus.publish("data_store.put", {"namespace": "test", "key": "b", "value": 2})
        
        time.sleep(0.2)
        manager.stop()
        
        # Verify file was created
        assert persist_path.exists()
        
        # Create new manager and verify data was loaded
        bus2 = MessageBus()
        manager2 = DataStoreManager(bus2, config)
        manager2.start()
        
        response_events = []
        bus2.subscribe("data_store.response", lambda d: response_events.append(d))
        
        bus2.publish("data_store.get", {"namespace": "test", "key": "a"})
        time.sleep(0.1)
        
        assert len(response_events) == 1
        assert response_events[0]["record"]["value"] == 1
        
        manager2.stop()


def test_data_store_handles_invalid_input():
    """Test that data store handles invalid input gracefully."""
    config = _base_config({"enabled": True})
    bus = MessageBus()
    manager = DataStoreManager(bus, config)
    manager.start()
    
    # Try to put without key
    bus.publish("data_store.put", {"namespace": "test", "value": 123})
    time.sleep(0.1)
    
    # Try to get without key
    bus.publish("data_store.get", {"namespace": "test"})
    time.sleep(0.1)
    
    # Try to delete without key
    bus.publish("data_store.delete", {"namespace": "test"})
    time.sleep(0.1)
    
    # Invalid data types
    bus.publish("data_store.put", "invalid")
    bus.publish("data_store.get", "invalid")
    bus.publish("data_store.delete", "invalid")
    bus.publish("data_store.list", "invalid")
    bus.publish("data_store.snapshot.request", "invalid")
    time.sleep(0.1)
    
    # Verify store is still empty
    response_events = []
    bus.subscribe("data_store.response", lambda d: response_events.append(d))
    bus.publish("data_store.list", {"namespace": "test"})
    time.sleep(0.1)
    
    assert len(response_events) == 1
    assert response_events[0]["keys"] == []
    
    manager.stop()
