from __future__ import annotations

from datetime import datetime
from typing import Optional

from modules.comms.types import MeshtasticClient


def get_changed_since(
    client: MeshtasticClient,
    timestamp: str | datetime,
    *,
    limit_per_type: Optional[int] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs = {"timestamp": timestamp, "timeout": timeout, "max_retries": retries}
    if limit_per_type is not None:
        kwargs["limit_per_type"] = limit_per_type
    return client.get_changed_since(**kwargs)
