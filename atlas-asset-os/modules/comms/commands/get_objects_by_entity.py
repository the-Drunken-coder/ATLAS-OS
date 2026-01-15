from __future__ import annotations

from modules.comms.types import MeshtasticClient


def get_objects_by_entity(
    client: MeshtasticClient,
    entity_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.get_objects_by_entity(
        entity_id=entity_id,
        limit=limit,
        offset=offset,
        timeout=timeout,
        max_retries=retries,
    )
