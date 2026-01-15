from __future__ import annotations

from modules.comms.types import MeshtasticClient


def get_entity_by_alias(client: MeshtasticClient, alias: str, *, timeout: float | None = None, retries: int | None = None):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.get_entity_by_alias(alias=alias, timeout=timeout, max_retries=retries)
