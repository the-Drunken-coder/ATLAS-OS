from __future__ import annotations

from typing import Optional

from atlas_asset_http_client_python.components import EntityComponents
from modules.comms.types import MeshtasticClient


def update_entity(
    client: MeshtasticClient,
    entity_id: str,
    *,
    subtype: Optional[str] = None,
    components: Optional[EntityComponents] = None,
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
