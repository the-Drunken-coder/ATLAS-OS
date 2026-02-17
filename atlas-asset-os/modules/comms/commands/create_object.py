from __future__ import annotations

from typing import Any, Optional

from modules.comms.types import MeshtasticClient


def create_object(
    client: MeshtasticClient,
    object_id: str,
    *,
    content_b64: str,
    usage_hint: Optional[str] = None,
    content_type: str,
    file_name: Optional[str] = None,
    type: Optional[str] = None,
    referenced_by: Optional[list[dict[str, Any]]] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.create_object(
        object_id=object_id,
        content_b64=content_b64,
        usage_hint=usage_hint,
        content_type=content_type,
        file_name=file_name,
        type=type,
        referenced_by=referenced_by,
        timeout=timeout,
        max_retries=retries,
    )
