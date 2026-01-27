from __future__ import annotations

from typing import Optional

from modules.comms.types import MeshtasticClient


def get_full_dataset(
    client: MeshtasticClient,
    *,
    entity_limit: Optional[int] = None,
    task_limit: Optional[int] = None,
    object_limit: Optional[int] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs = {"timeout": timeout, "max_retries": retries}
    if entity_limit is not None:
        kwargs["entity_limit"] = entity_limit
    if task_limit is not None:
        kwargs["task_limit"] = task_limit
    if object_limit is not None:
        kwargs["object_limit"] = object_limit
    return client.get_full_dataset(**kwargs)
