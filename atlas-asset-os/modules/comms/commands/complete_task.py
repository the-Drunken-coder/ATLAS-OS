from __future__ import annotations

from typing import Any

from modules.comms.types import MeshtasticClient


def complete_task(
    client: MeshtasticClient,
    task_id: str,
    *,
    result: Any = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.complete_task(
        task_id=task_id, result=result, timeout=timeout, max_retries=retries
    )
