from __future__ import annotations

from atlas_meshtastic_bridge.client import MeshtasticClient


def get_objects_by_task(
    client: MeshtasticClient,
    task_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.get_objects_by_task(
        task_id=task_id,
        limit=limit,
        offset=offset,
        timeout=timeout,
        max_retries=retries,
    )
