from __future__ import annotations

from typing import Any, Dict, Optional

from atlas_meshtastic_bridge.client import MeshtasticClient


def update_entity(
    client: MeshtasticClient,
    entity_id: str,
    *,
    subtype: Optional[str] = None,
    components: Optional[Dict[str, Any]] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.update_entity(
        entity_id=entity_id,
        subtype=subtype,
        components=components,
        timeout=timeout,
        max_retries=retries,
    )
