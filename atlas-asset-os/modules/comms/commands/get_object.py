from __future__ import annotations

from modules.comms.types import MeshtasticClient


def get_object(
    client: MeshtasticClient,
    object_id: str,
    *,
    download: bool | None = None,
    timeout: float | None = None,
    retries: int | None = None,
):
    if client is None:
        raise RuntimeError("Meshtastic client is not initialized")
    kwargs = {"object_id": object_id, "timeout": timeout, "max_retries": retries}
    if download is not None:
        kwargs["download"] = download
    return client.get_object(**kwargs)
