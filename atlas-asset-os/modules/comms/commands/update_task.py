from __future__ import annotations

from typing import Any, Optional

from atlas_asset_http_client_python.components import TaskComponents
from modules.comms.types import MeshtasticClient


def update_task(
    client: MeshtasticClient,
    task_id: str,
    *,
    status: Optional[str] = None,
    entity_id: Optional[str] = None,
    components: Optional[TaskComponents] = None,
    extra: Optional[Any] = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.update_task(
        task_id=task_id,
        status=status,
        entity_id=entity_id,
        components=components,
        extra=extra,
        timeout=timeout,
        max_retries=retries,
    )
