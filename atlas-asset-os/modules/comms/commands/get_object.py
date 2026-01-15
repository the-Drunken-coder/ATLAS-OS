from __future__ import annotations

from modules.comms.types import MeshtasticClient


def get_object(
    client: MeshtasticClient,
    object_id: str,
    *,
    download: bool = False,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    return client.get_object(
        object_id=object_id,
        download=download,
        timeout=timeout,
        max_retries=retries,
    )
