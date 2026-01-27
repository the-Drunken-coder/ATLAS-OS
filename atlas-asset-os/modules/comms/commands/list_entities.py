from __future__ import annotations

from modules.comms.types import MeshtasticClient


def list_entities(
    client: MeshtasticClient,
    limit: int | None = None,
    offset: int | None = None,
    *,
    timeout: float | None = None,
    retries: int | None = None,
):
    """List entities via the Meshtastic gateway."""
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs = {"timeout": timeout, "max_retries": retries}
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset
    return client.list_entities(**kwargs)
