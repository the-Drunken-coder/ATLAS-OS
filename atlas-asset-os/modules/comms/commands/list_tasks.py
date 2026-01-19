from __future__ import annotations

from typing import Optional

from modules.comms.types import MeshtasticClient


def list_tasks(
    client: MeshtasticClient,
    status: Optional[str] = None,
    limit: int = 25,
    *,
    timeout: float | None = None,
    retries: int | None = None,
):
    """List tasks via the Meshtastic gateway."""
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.list_tasks(
        status=status, limit=limit, timeout=timeout, max_retries=retries
    )
