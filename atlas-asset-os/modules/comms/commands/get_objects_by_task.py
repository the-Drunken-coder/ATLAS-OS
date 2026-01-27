from __future__ import annotations

from modules.comms.types import MeshtasticClient


def get_objects_by_task(
    client: MeshtasticClient,
    task_id: str,
    *,
    limit: int | None = None,
    offset: int | None = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs = {"task_id": task_id, "timeout": timeout, "max_retries": retries}
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset
    return client.get_objects_by_task(**kwargs)
