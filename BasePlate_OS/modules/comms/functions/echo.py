from __future__ import annotations

from typing import Any

from atlas_meshtastic_bridge.client import MeshtasticClient


def echo(client: MeshtasticClient, message: Any = "ping", *, timeout: float | None = None, retries: int | None = None):
    """Send an echo command via Meshtastic."""
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.test_echo(message=message, timeout=timeout, max_retries=retries)
