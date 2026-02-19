"""Atlas Command client for HTTP or Meshtastic transport."""

import asyncio
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_repo_root = Path(__file__).resolve().parent.parent.parent
_http_sdk_path = str(
    _repo_root
    / "Atlas_Client_SDKs"
    / "connection_packages"
    / "atlas_asset_http_client_python"
    / "src"
)
_mesh_sdk_path = str(
    _repo_root
    / "Atlas_Client_SDKs"
    / "connection_packages"
    / "atlas_meshtastic_bridge"
    / "src"
)

for sdk_path in (_http_sdk_path, _mesh_sdk_path):
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)

try:
    from atlas_asset_http_client_python import AtlasCommandHttpClient
    from atlas_asset_http_client_python.components import (
        EntityComponents,
        TaskCatalogComponent,
        TelemetryComponent,
    )
except ImportError as exc:
    raise ImportError(
        "atlas_asset_http_client_python not found. "
        "Install it from Atlas_Client_SDKs/connection_packages/atlas_asset_http_client_python "
        "or via pip: pip install atlas-asset-client"
    ) from exc

try:
    from atlas_meshtastic_bridge.cli import build_radio
    from atlas_meshtastic_bridge.client import MeshtasticClient
    from atlas_meshtastic_bridge.modes import load_mode_profile
    from atlas_meshtastic_bridge.reliability import strategy_from_name
    from atlas_meshtastic_bridge.transport import MeshtasticTransport

    _HAS_MESHTASTIC_BRIDGE = True
except ImportError:
    build_radio = None
    MeshtasticClient = None
    MeshtasticTransport = None
    load_mode_profile = None
    strategy_from_name = None
    _HAS_MESHTASTIC_BRIDGE = False


class CommsClient:
    """Synchronous wrapper for Atlas comms over HTTP or radio transport."""

    def __init__(self, comms_config, asset_config, radio_config=None):
        use_radio = comms_config.get("use_radio")
        if use_radio is None:
            # Backward compatibility with older config that used a string transport key.
            transport = str(comms_config.get("transport", "http")).lower()
            if transport not in {"http", "radio"}:
                log.warning("Unknown comms.transport '%s'; defaulting to http", transport)
                transport = "http"
            self._use_radio = transport == "radio"
        else:
            self._use_radio = bool(use_radio)

        self._simulated = comms_config.get("simulated", False)
        self._asset = asset_config
        self._base_url = comms_config.get("base_url", "").rstrip("/")
        self._token = comms_config.get("api_token")
        self._timeout = float(comms_config.get("timeout_s", 10))

        self._radio = radio_config or {}
        self._radio_simulated = bool(self._radio.get("simulated", False))
        self._radio_port = self._radio.get("radio_port")
        self._radio_node_id = self._radio.get("node_id")
        self._radio_gateway_node_id = self._radio.get("gateway_node_id", "gateway")
        self._radio_mode = self._radio.get("mode", "general")
        self._radio_timeout = float(self._radio.get("timeout_s", 15))
        self._radio_retries = int(self._radio.get("max_retries", 2))
        default_spool = "~/.atlas_meshtastic_spool_antenna_demo.json"
        self._radio_spool_path = os.path.expanduser(self._radio.get("spool_path", default_spool))

        self._known_task_ids = set()
        self._client = None
        self._loop = None
        self._radio_transport = None
        self._radio_client = None

    def connect(self):
        if self._simulated:
            log.info("Comms: simulated mode")
            return

        if self._use_radio:
            self._connect_radio()
            return

        self._connect_http()

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
        if self._radio_transport:
            try:
                self._radio_transport.close()
            except Exception:
                pass
            self._radio_transport = None
        self._radio_client = None

    # -- public API --

    def register_asset(self, supported_commands=None):
        asset = self._asset
        components = None
        if supported_commands:
            components = EntityComponents(
                task_catalog=TaskCatalogComponent(supported_tasks=supported_commands),
            )
        return self._create_entity(
            entity_id=asset["id"],
            entity_type=asset.get("type", "asset"),
            subtype=asset.get("model_id", "generic-asset"),
            alias=asset.get("name", asset["id"]),
            components=components,
        )

    def checkin(self, position):
        """Check in with GPS position. Returns list of new pending tasks."""
        entity_id = self._asset["id"]

        if self._simulated:
            log.info(
                "[SIM] checkin %s  lat=%.6f lon=%.6f",
                entity_id,
                position.get("latitude", 0),
                position.get("longitude", 0),
            )
            return []

        if self._use_radio:
            result = self._radio_request(
                "checkin_entity",
                entity_id=entity_id,
                latitude=position.get("latitude"),
                longitude=position.get("longitude"),
                heading_deg=position.get("heading_deg"),
            )
        else:
            try:
                result = self._run(
                    self._client.checkin_entity(
                        entity_id,
                        latitude=position.get("latitude"),
                        longitude=position.get("longitude"),
                        heading_deg=position.get("heading_deg"),
                    )
                )
            except Exception as exc:
                log.error("Checkin failed: %s", exc)
                return []

        tasks = result.get("tasks", []) if isinstance(result, dict) else []
        new_tasks = []
        for task in tasks:
            task_id = task.get("task_id")
            if task_id and task_id not in self._known_task_ids:
                self._known_task_ids.add(task_id)
                new_tasks.append(task)
        return new_tasks

    def create_entity(self, **kwargs):
        return self._create_entity(**kwargs)

    def start_task(self, task_id):
        if self._simulated:
            log.info("[SIM] start_task %s", task_id)
            return {}
        if self._use_radio:
            return self._radio_request("start_task", task_id=task_id)
        try:
            return self._run(self._client.start_task(task_id))
        except Exception as exc:
            log.error("Start task failed: %s", exc)
            return None

    def complete_task(self, task_id, result=None):
        if self._simulated:
            log.info("[SIM] complete_task %s", task_id)
            return {}
        if self._use_radio:
            return self._radio_request("complete_task", task_id=task_id, result=result)
        try:
            return self._run(self._client.complete_task(task_id, result=result))
        except Exception as exc:
            log.error("Complete task failed: %s", exc)
            return None

    def fail_task(self, task_id, error):
        if self._simulated:
            log.info("[SIM] fail_task %s: %s", task_id, error)
            return {}
        if self._use_radio:
            return self._radio_request("fail_task", task_id=task_id, error_message=error)
        try:
            return self._run(self._client.fail_task(task_id, error_message=error))
        except Exception as exc:
            log.error("Fail task failed: %s", exc)
            return None

    # -- internal --

    def _connect_http(self):
        if not self._base_url:
            log.error("comms.base_url not set; falling back to simulated mode")
            self._simulated = True
            return

        self._loop = asyncio.new_event_loop()
        self._client = AtlasCommandHttpClient(
            self._base_url,
            token=self._token,
            timeout=self._timeout,
        )

        try:
            self._run(self._client.get_health())
            log.info("Connected to Atlas Command over HTTP: %s", self._base_url)
        except Exception as exc:
            log.warning("HTTP health check failed (%s); will retry on first request", exc)

    def _connect_radio(self):
        if not _HAS_MESHTASTIC_BRIDGE:
            log.error(
                "atlas_meshtastic_bridge is unavailable. Install deps from "
                "Atlas_Client_SDKs/connection_packages/atlas_meshtastic_bridge."
            )
            self._simulated = True
            return
        if not self._radio_gateway_node_id:
            log.error("radio.gateway_node_id is required for radio transport")
            self._simulated = True
            return

        profile = {}
        try:
            profile = load_mode_profile(self._radio_mode) or {}
            log.info("Loaded radio mode profile: %s", self._radio_mode)
        except Exception as exc:
            log.warning("Failed to load radio mode profile '%s': %s", self._radio_mode, exc)

        reliability_name = profile.get("reliability_method")
        reliability = strategy_from_name(reliability_name)
        transport_kwargs = profile.get("transport", {}) or {}

        try:
            radio = build_radio(self._radio_simulated, self._radio_port, self._radio_node_id)
            self._radio_transport = MeshtasticTransport(
                radio,
                spool_path=self._radio_spool_path,
                reliability=reliability,
                enable_spool=True,
                **transport_kwargs,
            )
            self._radio_client = MeshtasticClient(
                self._radio_transport,
                gateway_node_id=self._radio_gateway_node_id,
            )
        except Exception as exc:
            log.error("Failed to initialize radio transport: %s", exc)
            self._simulated = True
            return

        log.info(
            "Connected to Atlas via radio gateway=%s simulate=%s port=%s",
            self._radio_gateway_node_id,
            self._radio_simulated,
            self._radio_port,
        )

        result = self._radio_request("health_check")
        if result is None:
            log.warning("Radio health check failed; will retry on first request")

    def _run(self, coro):
        """Run an async coroutine on our persistent event loop."""
        return self._loop.run_until_complete(coro)

    @staticmethod
    def _dict_to_entity_components(value):
        """Convert a plain dict to an EntityComponents instance."""
        built = {}
        for key, item in value.items():
            if key == "telemetry" and isinstance(item, dict):
                built[key] = TelemetryComponent(**item)
            elif key == "task_catalog" and isinstance(item, dict):
                built[key] = TaskCatalogComponent(**item)
            else:
                built[key] = item
        return EntityComponents(**built)

    def _radio_request(self, method_name, **kwargs):
        if self._radio_client is None:
            log.error("Radio client is not connected")
            return None

        handler = getattr(self._radio_client, method_name, None)
        if handler is None:
            log.error("Radio client has no method '%s'", method_name)
            return None

        try:
            response = handler(
                timeout=self._radio_timeout,
                max_retries=self._radio_retries,
                **kwargs,
            )
        except Exception as exc:
            log.error("Radio request %s failed: %s", method_name, exc)
            return None

        return self._unwrap_radio_response(method_name, response)

    @staticmethod
    def _unwrap_radio_response(method_name, response):
        if response is None:
            return None
        response_type = getattr(response, "type", None)
        payload = getattr(response, "data", {}) or {}

        if response_type == "error":
            message = payload.get("error") if isinstance(payload, dict) else payload
            log.error("Radio %s returned error: %s", method_name, message)
            return None
        if response_type and response_type != "response":
            log.error("Unexpected radio response type for %s: %s", method_name, response_type)
            return None
        if isinstance(payload, dict) and "result" in payload:
            return payload["result"]
        return payload

    def _create_entity(self, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        entity_id = kwargs.get("entity_id", "?")

        if self._simulated:
            log.info("[SIM] create_entity %s", entity_id)
            return {}

        components = kwargs.get("components")
        if isinstance(components, dict):
            components = self._dict_to_entity_components(components)

        if self._use_radio:
            return self._radio_request(
                "create_entity",
                entity_id=kwargs["entity_id"],
                entity_type=kwargs.get("entity_type", "track"),
                alias=kwargs.get("alias", entity_id),
                subtype=kwargs.get("subtype", "unknown"),
                components=components,
            )

        try:
            return self._run(
                self._client.create_entity(
                    entity_id=kwargs["entity_id"],
                    entity_type=kwargs.get("entity_type", "track"),
                    alias=kwargs.get("alias", entity_id),
                    subtype=kwargs.get("subtype", "unknown"),
                    components=components,
                )
            )
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status == 409:
                log.info("Entity %s already exists", entity_id)
                return {"entity_id": entity_id}
            log.error("Create entity failed: %s", exc)
            return None
