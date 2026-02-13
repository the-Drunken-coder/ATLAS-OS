from __future__ import annotations

from typing import Optional

from atlas_asset_http_client_python.components import EntityComponents
from modules.comms.types import MeshtasticClient


def create_entity(
    client: MeshtasticClient,
    entity_id: str,
    entity_type: str,
    alias: str,
    subtype: str,
    *,
    components: Optional[EntityComponents] = None,
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
