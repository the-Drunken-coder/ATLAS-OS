from __future__ import annotations

from typing import Optional

from atlas_meshtastic_bridge.client import MeshtasticClient


def remove_object_reference(
    client: MeshtasticClient,
    object_id: str,
    *,
    entity_id: Optional[str] = None,
    task_id: Optional[str] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.remove_object_reference(
        object_id=object_id,
        entity_id=entity_id,
        task_id=task_id,
        timeout=timeout,
        max_retries=retries,
    )
