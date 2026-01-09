from __future__ import annotations

from datetime import datetime
from typing import Optional

from atlas_meshtastic_bridge.client import MeshtasticClient


def get_changed_since(
    client: MeshtasticClient,
    since: str | datetime,
    *,
    limit_per_type: Optional[int] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.get_changed_since(
        since=since,
        limit_per_type=limit_per_type,
        timeout=timeout,
        max_retries=retries,
    )
