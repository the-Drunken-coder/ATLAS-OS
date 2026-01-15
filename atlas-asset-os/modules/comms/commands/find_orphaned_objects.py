from __future__ import annotations

from modules.comms.types import MeshtasticClient


def find_orphaned_objects(
    client: MeshtasticClient,
    *,
    limit: int = 100,
    offset: int = 0,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.find_orphaned_objects(
        limit=limit,
        offset=offset,
        timeout=timeout,
        max_retries=retries,
    )
