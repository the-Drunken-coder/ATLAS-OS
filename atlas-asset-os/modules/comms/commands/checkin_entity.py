from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from modules.comms.types import MeshtasticClient


def checkin_entity(
    client: MeshtasticClient,
    entity_id: str,
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    altitude_m: Optional[float] = None,
    speed_m_s: Optional[float] = None,
    heading_deg: Optional[float] = None,
    status_filter: Optional[str] = None,
    limit: Optional[int] = None,
    since: Optional[str | datetime] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs: dict[str, Any] = {
        "entity_id": entity_id,
        "timeout": timeout,
        "max_retries": retries,
    }
    if latitude is not None:
        kwargs["latitude"] = latitude
    if longitude is not None:
        kwargs["longitude"] = longitude
    if altitude_m is not None:
        kwargs["altitude_m"] = altitude_m
    if speed_m_s is not None:
        kwargs["speed_m_s"] = speed_m_s
    if heading_deg is not None:
        kwargs["heading_deg"] = heading_deg
    if status_filter is not None:
        kwargs["status_filter"] = status_filter
    if limit is not None:
        kwargs["limit"] = limit
    if since is not None:
        kwargs["since"] = since
    return client.checkin_entity(**kwargs)
