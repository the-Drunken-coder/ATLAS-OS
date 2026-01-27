from __future__ import annotations

from typing import Any, Optional

from modules.comms.types import MeshtasticClient


def list_objects(
    client: MeshtasticClient,
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    content_type: Optional[str] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs: dict[str, Any] = {"timeout": timeout, "max_retries": retries}
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset
    if content_type is not None:
        kwargs["content_type"] = content_type
    return client.list_objects(**kwargs)
