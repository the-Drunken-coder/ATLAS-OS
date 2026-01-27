from __future__ import annotations

from typing import Any, Optional

from modules.comms.types import MeshtasticClient


def list_tasks(
    client: MeshtasticClient,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    timeout: float | None = None,
    retries: int | None = None,
):
    """List tasks via the Meshtastic gateway."""
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs: dict[str, Any] = {"timeout": timeout, "max_retries": retries}
    if status is not None:
        kwargs["status"] = status
    if limit is not None:
        kwargs["limit"] = limit
    return client.list_tasks(**kwargs)
