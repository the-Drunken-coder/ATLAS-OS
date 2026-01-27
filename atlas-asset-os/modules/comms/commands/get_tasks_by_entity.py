from __future__ import annotations

from modules.comms.types import MeshtasticClient


def get_tasks_by_entity(
    client: MeshtasticClient,
    entity_id: str,
    *,
    limit: int | None = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs = {"entity_id": entity_id, "timeout": timeout, "max_retries": retries}
    if limit is not None:
        kwargs["limit"] = limit
    return client.get_tasks_by_entity(**kwargs)
