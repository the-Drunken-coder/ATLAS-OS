import threading
import time
from typing import Any, Dict


class SensorWorker:
    """Base class for sensor workers that run capture + analysis in one loop."""

    def __init__(self, bus, device_cfg: Dict[str, Any], config: Dict[str, Any]):
        self.bus = bus
        self.device_cfg = device_cfg
        self.config = config
        self.sensor_id = str(device_cfg.get("id", "unknown"))
        self.sensor_type = str(device_cfg.get("type", "unknown"))
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def run(self) -> None:
        """Override in subclasses. Should loop while self._running."""
        while self._running:
            time.sleep(1)

    def publish_output(self, data: Dict[str, Any]) -> None:
        payload = {
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type,
            "timestamp": time.time(),
            "data": data,
        }
        self.bus.publish("sensor.output", payload)
