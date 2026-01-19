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
        self._registered_commands: Dict[str, str] = {}

        module_cfg = self.get_module_config()
        devices = module_cfg.get("devices", [])
        if isinstance(devices, list):
            self._devices = devices
        else:
            LOGGER.warning(
                "Sensors config missing devices list; got %s", type(devices).__name__
            )

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

            self._register_device_commands(sensor_id, device_cfg)

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
        self._unregister_device_commands()
        for sensor_id, worker in list(self._workers.items()):
            try:
                worker.stop()
                LOGGER.info("Stopped sensor worker: %s", sensor_id)
            except Exception as exc:
                LOGGER.warning("Failed to stop sensor worker %s: %s", sensor_id, exc)
        self._workers.clear()

    def _register_device_commands(self, sensor_id: str, device_cfg: dict) -> None:
        commands = device_cfg.get("commands")
        if not isinstance(commands, list):
            return
        for command in commands:
            if not command:
                continue
            command_name = str(command)
            handler = self._build_device_handler(sensor_id, command_name)
            self.bus.publish(
                "commands.register",
                {"command": command_name, "handler": handler},
            )
            self._registered_commands[command_name] = sensor_id

    def _unregister_device_commands(self) -> None:
        for command_name in list(self._registered_commands.keys()):
            self.bus.publish("commands.unregister", {"command": command_name})
        self._registered_commands.clear()

    def _build_device_handler(self, sensor_id: str, command: str):
        def _handler(parameters: dict) -> dict:
            self.bus.publish(
                "sensor.command",
                {
                    "sensor_id": sensor_id,
                    "command": command,
                    "parameters": parameters,
                },
            )
            return {"status": "sent"}

        return _handler
