from __future__ import annotations

from typing import Optional

from modules.comms.types import MeshtasticClient


def list_objects(
    client: MeshtasticClient,
    *,
    limit: int = 20,
    offset: int = 0,
    content_type: Optional[str] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.list_objects(
        limit=limit,
        offset=offset,
        content_type=content_type,
        timeout=timeout,
        max_retries=retries,
    )
