from __future__ import annotations

from atlas_meshtastic_bridge.client import MeshtasticClient


def get_tasks_by_entity(
    client: MeshtasticClient,
    entity_id: str,
    *,
    limit: int = 25,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.get_tasks_by_entity(
        entity_id=entity_id,
        limit=limit,
        timeout=timeout,
        max_retries=retries,
    )
