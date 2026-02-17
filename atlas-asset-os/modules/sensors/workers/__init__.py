from modules.sensors.workers.base import SensorWorker
from modules.sensors.workers.camera_bearing import CameraBearingWorker

WORKER_REGISTRY = {
    "camera_bearing": CameraBearingWorker,
}

__all__ = ["SensorWorker", "CameraBearingWorker", "WORKER_REGISTRY"]
