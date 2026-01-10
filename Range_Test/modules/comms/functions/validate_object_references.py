from __future__ import annotations

from atlas_meshtastic_bridge.client import MeshtasticClient


def validate_object_references(
    client: MeshtasticClient,
    object_id: str,
    *,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.validate_object_references(
        object_id=object_id,
        timeout=timeout,
        max_retries=retries,
    )
