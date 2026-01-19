import logging
import time
import threading
from typing import Any, Dict

LOGGER = logging.getLogger("modules.operations.registration")


def register_asset(bus, config: Dict[str, Any], timeout: float = 10.0) -> bool:
    """
    Register asset with Atlas Command via comms bus.

    Uses create_entity with retry logic (up to 3 attempts with exponential backoff).

    Args:
        bus: MessageBus instance
        config: Configuration dictionary containing atlas.asset settings
        timeout: Timeout per attempt in seconds

    Returns:
        True if registration succeeded, False otherwise
    """
    asset_cfg = config.get("atlas", {}).get("asset", {})
    if not asset_cfg:
        LOGGER.error("No asset configuration found in config")
        return False

    entity_id = asset_cfg.get("id")
    entity_type = str(asset_cfg.get("type", "asset")).lower()
    alias = asset_cfg.get("name", entity_id)
    model_id = asset_cfg.get("model_id", "generic-asset")

    if not entity_id:
        LOGGER.error("Asset ID not found in configuration")
        return False

    allowed_entity_types = {"asset", "track", "geofeature"}
    if entity_type not in allowed_entity_types:
        LOGGER.error(
            "Invalid asset entity type '%s'. Allowed values: %s",
            entity_type,
            ", ".join(sorted(allowed_entity_types)),
        )
        return False

    # Prepare registration request
    registration_result = {"success": False, "error": None}
    registration_event = threading.Event()

    def handle_response(data: Any) -> None:
        """Handle comms.response for registration."""
        if not isinstance(data, dict):
            return

        func_name = data.get("function")
        if func_name != "create_entity":
            return

        if data.get("ok", False):
            registration_result["success"] = True
            LOGGER.info("Asset registration successful: %s (%s)", entity_id, alias)
        else:
            registration_result["error"] = data.get("error", "Unknown error")
            LOGGER.warning("Asset registration failed: %s", registration_result["error"])

        registration_event.set()

    # Subscribe to comms responses
    bus.subscribe("comms.response", handle_response)

    try:
        # Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
        max_attempts = 3
        for attempt in range(max_attempts):
            if attempt > 0:
                delay = 2.0 ** (attempt - 1)  # 1s, 2s, 4s
                LOGGER.info(
                    "Retrying asset registration (attempt %d/%d) after %.1fs...",
                    attempt + 1,
                    max_attempts,
                    delay,
                )
                time.sleep(delay)

            # Reset event and result
            registration_event.clear()
            registration_result["success"] = False
            registration_result["error"] = None

            # Prepare create_entity arguments
            create_args = {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "alias": alias,
                "subtype": model_id,
            }

            # Publish registration request
            request_id = f"reg-{int(time.time() * 1000)}"
            LOGGER.info(
                "Registering asset: id=%s, type=%s, alias=%s, model=%s",
                entity_id,
                entity_type,
                alias,
                model_id,
            )

            bus.publish(
                "comms.request",
                {
                    "function": "create_entity",
                    "args": create_args,
                    "request_id": request_id,
                },
            )

            # Wait for response with timeout
            if registration_event.wait(timeout=timeout):
                if registration_result["success"]:
                    return True
                # If failed but not last attempt, continue to retry
                if attempt < max_attempts - 1:
                    LOGGER.debug("Registration attempt %d failed, will retry", attempt + 1)
                    continue
            else:
                LOGGER.warning("Registration request timed out after %.1fs", timeout)
                if attempt < max_attempts - 1:
                    continue

        # All attempts failed
        LOGGER.error(
            "Asset registration failed after %d attempts. Last error: %s",
            max_attempts,
            registration_result.get("error", "Timeout"),
        )
        return False

    finally:
        # Unsubscribe from responses
        bus.unsubscribe("comms.response", handle_response)
