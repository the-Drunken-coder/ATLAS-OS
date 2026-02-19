"""Atlas Command HTTP client.

Uses atlas_asset_http_client_python (local SDK install preferred, pip fallback).
Wraps the async client for use in our synchronous main loop.
"""

import asyncio
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# Try local SDK install first, then fall back to pip package
_sdk_path = str(Path(__file__).resolve().parent.parent.parent
                / "Atlas_Client_SDKs" / "connection_packages"
                / "atlas_asset_http_client_python" / "src")

if _sdk_path not in sys.path:
    sys.path.insert(0, _sdk_path)

try:
    from atlas_asset_http_client_python import AtlasCommandHttpClient
    from atlas_asset_http_client_python.components import (
        EntityComponents,
        TaskCatalogComponent,
        TelemetryComponent,
    )
    log.debug("Using local atlas_asset_http_client_python from SDK")
except ImportError:
    sys.path.remove(_sdk_path)
    try:
        from atlas_asset_http_client_python import AtlasCommandHttpClient
        from atlas_asset_http_client_python.components import (
            EntityComponents,
            TaskCatalogComponent,
            TelemetryComponent,
        )
        log.debug("Using pip-installed atlas_asset_http_client_python")
    except ImportError:
        raise ImportError(
            "atlas_asset_http_client_python not found. "
            "Install it from Atlas_Client_SDKs/connection_packages/atlas_asset_http_client_python "
            "or via pip: pip install atlas-asset-client"
        )


class CommsClient:
    """Synchronous wrapper around AtlasCommandHttpClient."""

    def __init__(self, comms_config, asset_config):
        self._simulated = comms_config.get("simulated", False)
        self._asset = asset_config
        self._base_url = comms_config.get("base_url", "").rstrip("/")
        self._token = comms_config.get("api_token")
        self._timeout = float(comms_config.get("timeout_s", 10))
        self._known_task_ids = set()
        self._client = None
        self._loop = None

    def connect(self):
        if self._simulated:
            log.info("Comms: simulated mode")
            return

        if not self._base_url:
            log.error("comms.base_url not set — falling back to simulated mode")
            self._simulated = True
            return

        self._loop = asyncio.new_event_loop()
        self._client = AtlasCommandHttpClient(
            self._base_url, token=self._token, timeout=self._timeout,
        )

        try:
            self._run(self._client.get_health())
            log.info("Connected to Atlas Command at %s", self._base_url)
        except Exception as exc:
            log.warning("Health check failed (%s) — will retry on first request", exc)

    def close(self):
        if self._client:
            try:
                self._run(self._client.aclose())
            except Exception:
                pass
            self._client = None
        if self._loop:
            self._loop.close()
            self._loop = None

    # -- public API --

    def register_asset(self, supported_commands=None):
        a = self._asset
        components = None
        if supported_commands:
            components = EntityComponents(
                task_catalog=TaskCatalogComponent(supported_tasks=supported_commands),
            )
        return self._create_entity(
            entity_id=a["id"],
            entity_type=a.get("type", "asset"),
            subtype=a.get("model_id", "generic-asset"),
            alias=a.get("name", a["id"]),
            components=components,
        )

    def checkin(self, position):
        """Check in with GPS position. Returns list of new pending tasks."""
        entity_id = self._asset["id"]

        if self._simulated:
            log.info("[SIM] checkin %s  lat=%.6f lon=%.6f",
                     entity_id, position.get("latitude", 0), position.get("longitude", 0))
            return []

        try:
            result = self._run(self._client.checkin_entity(
                entity_id,
                latitude=position.get("latitude"),
                longitude=position.get("longitude"),
                heading_deg=position.get("heading_deg"),
            ))
        except Exception as exc:
            log.error("Checkin failed: %s", exc)
            return []

        tasks = result.get("tasks", []) if isinstance(result, dict) else []
        new_tasks = []
        for t in tasks:
            tid = t.get("task_id")
            if tid and tid not in self._known_task_ids:
                self._known_task_ids.add(tid)
                new_tasks.append(t)
        return new_tasks

    def create_entity(self, **kwargs):
        return self._create_entity(**kwargs)

    def start_task(self, task_id):
        if self._simulated:
            log.info("[SIM] start_task %s", task_id)
            return {}
        try:
            return self._run(self._client.start_task(task_id))
        except Exception as exc:
            log.error("Start task failed: %s", exc)
            return None

    def complete_task(self, task_id, result=None):
        if self._simulated:
            log.info("[SIM] complete_task %s", task_id)
            return {}
        try:
            return self._run(self._client.complete_task(task_id, result=result))
        except Exception as exc:
            log.error("Complete task failed: %s", exc)
            return None

    def fail_task(self, task_id, error):
        if self._simulated:
            log.info("[SIM] fail_task %s: %s", task_id, error)
            return {}
        try:
            return self._run(self._client.fail_task(task_id, error_message=error))
        except Exception as exc:
            log.error("Fail task failed: %s", exc)
            return None

    # -- internal --

    def _run(self, coro):
        """Run an async coroutine on our persistent event loop."""
        return self._loop.run_until_complete(coro)

    @staticmethod
    def _dict_to_entity_components(d):
        """Convert a plain dict to an EntityComponents instance."""
        built = {}
        for key, value in d.items():
            if key == "telemetry" and isinstance(value, dict):
                built[key] = TelemetryComponent(**value)
            elif key == "task_catalog" and isinstance(value, dict):
                built[key] = TaskCatalogComponent(**value)
            else:
                # Pass through as-is (custom_ prefixed or already typed)
                built[key] = value
        return EntityComponents(**built)

    def _create_entity(self, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        entity_id = kwargs.get("entity_id", "?")

        if self._simulated:
            log.info("[SIM] create_entity %s", entity_id)
            return {}

        # Convert plain dict components to EntityComponents if needed
        components = kwargs.get("components")
        if isinstance(components, dict):
            components = self._dict_to_entity_components(components)

        try:
            return self._run(self._client.create_entity(
                entity_id=kwargs["entity_id"],
                entity_type=kwargs.get("entity_type", "track"),
                alias=kwargs.get("alias", entity_id),
                subtype=kwargs.get("subtype", "unknown"),
                components=components,
            ))
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status == 409:
                log.info("Entity %s already exists", entity_id)
                return {"entity_id": entity_id}
            log.error("Create entity failed: %s", exc)
            return None
