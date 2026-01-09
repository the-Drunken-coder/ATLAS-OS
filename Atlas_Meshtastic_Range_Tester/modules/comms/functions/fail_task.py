from __future__ import annotations

from typing import Any, Optional

from atlas_meshtastic_bridge.client import MeshtasticClient


def fail_task(
    client: MeshtasticClient,
    task_id: str,
    *,
    error_message: Optional[str] = None,
    error_details: Any = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.fail_task(
        task_id=task_id,
        error_message=error_message,
        error_details=error_details,
        timeout=timeout,
        max_retries=retries,
    )
