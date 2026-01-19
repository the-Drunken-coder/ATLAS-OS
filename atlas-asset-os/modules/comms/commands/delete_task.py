from __future__ import annotations

from modules.comms.types import MeshtasticClient


def delete_task(
    client: MeshtasticClient,
    task_id: str,
    *,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.delete_task(task_id=task_id, timeout=timeout, max_retries=retries)
