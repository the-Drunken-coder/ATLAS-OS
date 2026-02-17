from __future__ import annotations

from typing import Any, Optional

from modules.comms.types import MeshtasticClient


def update_object(
    client: MeshtasticClient,
    object_id: str,
    *,
    usage_hints: Optional[list[str]] = None,
    referenced_by: Optional[list[dict[str, Any]]] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.update_object(
        object_id=object_id,
        usage_hints=usage_hints,
        referenced_by=referenced_by,
        timeout=timeout,
        max_retries=retries,
    )
