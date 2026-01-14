from __future__ import annotations

from typing import Optional

from atlas_meshtastic_bridge.client import MeshtasticClient


def update_telemetry(
    client: MeshtasticClient,
    entity_id: str,
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    altitude_m: Optional[float] = None,
    speed_m_s: Optional[float] = None,
    heading_deg: Optional[float] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.update_telemetry(
        entity_id=entity_id,
        latitude=latitude,
        longitude=longitude,
        altitude_m=altitude_m,
        speed_m_s=speed_m_s,
        heading_deg=heading_deg,
        timeout=timeout,
        max_retries=retries,
    )
