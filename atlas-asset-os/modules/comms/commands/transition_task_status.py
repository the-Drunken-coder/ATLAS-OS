from __future__ import annotations

from modules.comms.types import MeshtasticClient


def transition_task_status(
    client: MeshtasticClient,
    task_id: str,
    status: str,
    *,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.transition_task_status(
        task_id=task_id,
        status=status,
        timeout=timeout,
        max_retries=retries,
    )
