import logging
from typing import Dict, List

from modules.module_base import ModuleBase
from modules.sensors.workers import WORKER_REGISTRY, SensorWorker

LOGGER = logging.getLogger("modules.sensors")


class SensorsManager(ModuleBase):
    """Sensor manager that runs worker plugins for capture + analysis."""

    MODULE_NAME = "sensors"
    MODULE_VERSION = "1.0.0"
    DEPENDENCIES: List[str] = []

    def __init__(self, bus, config):
        super().__init__(bus, config)
        self._workers: Dict[str, SensorWorker] = {}
        self._devices = []

        module_cfg = self.get_module_config()
        devices = module_cfg.get("devices", [])
        if isinstance(devices, list):
            self._devices = devices
        else:
            LOGGER.warning("Sensors config missing devices list; got %s", type(devices).__name__)

    def start(self) -> None:
        self._logger.info("Starting Sensors Manager")
        self.running = True

        for device_cfg in self._devices:
            if not isinstance(device_cfg, dict):
                LOGGER.warning("Skipping invalid sensor config: %s", device_cfg)
                continue
            if not device_cfg.get("enabled", True):
                continue
            sensor_id = device_cfg.get("id")
            sensor_type = device_cfg.get("type")
            if not sensor_id or not sensor_type:
                LOGGER.warning("Sensor config missing id/type: %s", device_cfg)
                continue

            worker_cls = WORKER_REGISTRY.get(str(sensor_type))
            if worker_cls is None:
                LOGGER.warning("No worker registered for sensor type '%s'", sensor_type)
                continue

            worker = worker_cls(self.bus, device_cfg, self.config)
            self._workers[sensor_id] = worker
            worker.start()
            LOGGER.info("Started sensor worker: %s (%s)", sensor_id, sensor_type)

    def stop(self) -> None:
        self._logger.info("Stopping Sensors Manager")
        self.running = False
        for sensor_id, worker in list(self._workers.items()):
            try:
                worker.stop()
                LOGGER.info("Stopped sensor worker: %s", sensor_id)
            except Exception as exc:
                LOGGER.warning("Failed to stop sensor worker %s: %s", sensor_id, exc)
        self._workers.clear()
