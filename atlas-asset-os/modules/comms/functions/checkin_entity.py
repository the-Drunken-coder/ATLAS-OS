from __future__ import annotations

from datetime import datetime
from typing import Optional

from atlas_meshtastic_bridge.client import MeshtasticClient


def checkin_entity(
    client: MeshtasticClient,
    entity_id: str,
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    altitude_m: Optional[float] = None,
    speed_m_s: Optional[float] = None,
    heading_deg: Optional[float] = None,
    status_filter: str = "pending,in_progress",
    limit: int = 10,
    since: Optional[str | datetime] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.checkin_entity(
        entity_id=entity_id,
        latitude=latitude,
        longitude=longitude,
        altitude_m=altitude_m,
        speed_m_s=speed_m_s,
        heading_deg=heading_deg,
        status_filter=status_filter,
        limit=limit,
        since=since,
        timeout=timeout,
        max_retries=retries,
    )
