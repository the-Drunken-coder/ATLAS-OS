from __future__ import annotations

from typing import Any, Dict, Optional

from atlas_meshtastic_bridge.client import MeshtasticClient


def create_entity(
    client: MeshtasticClient,
    entity_id: str,
    entity_type: str,
    alias: str,
    subtype: str,
    *,
    components: Optional[Dict[str, Any]] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.create_entity(
        entity_id=entity_id,
        entity_type=entity_type,
        alias=alias,
        subtype=subtype,
        components=components,
        timeout=timeout,
        max_retries=retries,
    )
