from __future__ import annotations

from modules.comms.types import MeshtasticClient


def find_orphaned_objects(
    client: MeshtasticClient,
    *,
    limit: int | None = None,
    offset: int | None = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs = {"timeout": timeout, "max_retries": retries}
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset
    return client.find_orphaned_objects(**kwargs)
