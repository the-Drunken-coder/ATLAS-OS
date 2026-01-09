from __future__ import annotations

from atlas_meshtastic_bridge.client import MeshtasticClient


def get_entity(client: MeshtasticClient, entity_id: str, *, timeout: float | None = None, retries: int | None = None):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.get_entity(entity_id=entity_id, timeout=timeout, max_retries=retries)
