from __future__ import annotations

from modules.comms.types import MeshtasticClient


def get_object_references(
    client: MeshtasticClient,
    object_id: str,
    *,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.get_object_references(
        object_id=object_id,
        timeout=timeout,
        max_retries=retries,
    )
