import time
from typing import Any, Dict

from modules.sensors.workers.base import SensorWorker


class CameraBearingWorker(SensorWorker):
    """Example camera worker that outputs bearing/elevation analysis."""

    def __init__(self, bus, device_cfg: Dict[str, Any], config: Dict[str, Any]):
        super().__init__(bus, device_cfg, config)
        self._interval_s = float(device_cfg.get("interval_s", 1.0))
        self._bearing_deg = float(device_cfg.get("bearing_deg", 0.0))
        self._elevation_deg = float(device_cfg.get("elevation_deg", 0.0))
        self._confidence = float(device_cfg.get("confidence", 0.5))

    def run(self) -> None:
        while self._running:
            self.publish_output(
                {
                    "bearing_deg": self._bearing_deg,
                    "elevation_deg": self._elevation_deg,
                    "confidence": self._confidence,
                }
            )
            time.sleep(self._interval_s)
