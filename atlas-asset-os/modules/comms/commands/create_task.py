from __future__ import annotations

from typing import Any, Dict, Optional

from modules.comms.types import MeshtasticClient


def create_task(
    client: MeshtasticClient,
    task_id: str,
    *,
    status: Optional[str] = None,
    entity_id: Optional[str] = None,
    components: Optional[Dict[str, Any]] = None,
    extra: Optional[Any] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.create_task(
        task_id=task_id,
        status=status,
        entity_id=entity_id,
        components=components,
        extra=extra,
        timeout=timeout,
        max_retries=retries,
    )
