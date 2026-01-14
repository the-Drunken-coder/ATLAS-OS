from __future__ import annotations

from atlas_meshtastic_bridge.client import MeshtasticClient


def health_check(client: MeshtasticClient, *, timeout: float | None = None, retries: int | None = None):
    """Check Atlas Command health status via Meshtastic."""
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.health_check(timeout=timeout, max_retries=retries)
