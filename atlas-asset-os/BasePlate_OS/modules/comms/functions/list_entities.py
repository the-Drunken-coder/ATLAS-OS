from __future__ import annotations

from atlas_meshtastic_bridge.client import MeshtasticClient


def list_entities(client: MeshtasticClient, limit: int = 5, offset: int = 0, *, timeout: float | None = None, retries: int | None = None):
    """List entities via the Meshtastic gateway."""
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.list_entities(limit=limit, offset=offset, timeout=timeout, max_retries=retries)
