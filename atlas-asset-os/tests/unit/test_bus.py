"""Unit tests for the central MessageBus."""

import sys
from pathlib import Path

# Add framework to path
_FRAMEWORK_DIR = Path(__file__).resolve().parents[3] / "framework"
if str(_FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_DIR))

from framework.bus import MessageBus  # noqa: E402


def test_bus_initialization():
    """Verify bus initializes in a running state with no subscribers."""
    bus = MessageBus()
    assert bus._running is True
    assert bus._subscribers == {}


def test_bus_subscribe_publish():
    """Verify basic subscribe and publish functionality."""
    bus = MessageBus()
    received_data = []

    def handler(data):
        received_data.append(data)

    bus.subscribe("test.topic", handler)
    bus.publish("test.topic", {"key": "value"})

    assert len(received_data) == 1
    assert received_data[0] == {"key": "value"}


def test_bus_multiple_subscribers():
    """Verify multiple subscribers to the same topic all receive the message."""
    bus = MessageBus()
    received_a = []
    received_b = []

    bus.subscribe("test.topic", lambda d: received_a.append(d))
    bus.subscribe("test.topic", lambda d: received_b.append(d))

    bus.publish("test.topic", "hello")

    assert received_a == ["hello"]
    assert received_b == ["hello"]


def test_bus_handler_exception():
    """Verify that an exception in one handler does not prevent others from receiving."""
    bus = MessageBus()
    received_data = []

    def failing_handler(data):
        raise RuntimeError("Handler failed!")

    def working_handler(data):
        received_data.append(data)

    bus.subscribe("test.topic", failing_handler)
    bus.subscribe("test.topic", working_handler)

    # This should not raise an exception to the caller
    bus.publish("test.topic", "test")

    assert received_data == ["test"]


def test_bus_publish_not_running():
    """Verify that publishing does nothing if the bus is not running."""
    bus = MessageBus()
    received_data = []
    bus.subscribe("test", lambda d: received_data.append(d))

    bus.shutdown()
    bus.publish("test", "data")

    assert len(received_data) == 0


def test_bus_publish_no_subscribers():
    """Verify that publishing to a topic with no subscribers works fine."""
    bus = MessageBus()
    # Should not raise any errors
    bus.publish("non.existent.topic", "some data")


def test_bus_logging_records_events(tmp_path):
    """Verify bus logging writes publish/subscribe events when enabled."""
    log_file = tmp_path / "bus.log"
    bus = MessageBus(logging_config={"enabled": True, "log_file": str(log_file)})

    received = []

    def handler(data):
        received.append(data)

    bus.subscribe("topic", handler)
    bus.publish("topic", {"msg": 1})
    bus.shutdown()

    with open(log_file, "r", encoding="utf-8") as f:
        contents = f.read()

    assert "subscribe topic=topic" in contents
    assert "publish topic=topic data={'msg': 1}" in contents


def test_bus_logging_unsubscribe(tmp_path):
    """Verify unsubscribe is logged when enabled."""
    log_file = tmp_path / "bus_unsub.log"
    bus = MessageBus(logging_config={"enabled": True, "log_file": str(log_file)})

    def handler(data):
        pass

    bus.subscribe("topic", handler)
    bus.unsubscribe("topic", handler)
    bus.shutdown()

    with open(log_file, "r", encoding="utf-8") as f:
        contents = f.read()

    assert "unsubscribe topic=topic" in contents
