import json
import logging
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from modules.module_base import ModuleBase
from modules.comms.commands import FUNCTION_REGISTRY
from modules.comms.transports.meshtastic import build_meshtastic_client
from modules.comms.transports.wifi import build_wifi_client
from modules.comms.types import MeshtasticClient

LOGGER = logging.getLogger("modules.comms")


class CommsManager(ModuleBase):
    """Communications manager for Atlas Command connections."""

    MODULE_NAME = "comms"
    MODULE_VERSION = "1.0.0"
    DEPENDENCIES: List[str] = []  # No dependencies, starts first

    def __init__(self, bus, config):
        super().__init__(bus, config)
        self._thread: Optional[threading.Thread] = None

        comms_cfg = self.get_module_config()
        self.simulated = bool(comms_cfg.get("simulated", False))
        self.gateway_node_id = comms_cfg.get("gateway_node_id") or "gateway"
        self.method = None
        self.enabled_methods = self._resolve_enabled_methods(comms_cfg)
        self.priority_methods = self._load_priority_methods()
        self.wifi_config = comms_cfg.get("wifi", {})

        # "auto" means auto-detect the radio port (same as None/null)
        radio_port_cfg = comms_cfg.get("radio_port")
        self.radio_port = None if radio_port_cfg in (None, "auto") else radio_port_cfg

        self.mode = comms_cfg.get("mode") or "general"
        self.spool_path = os.path.expanduser(
            comms_cfg.get("spool_path", "~/.baseplate_comm_spool.json")
        )

        self.client: Optional[MeshtasticClient] = None
        self.functions: Dict[str, Callable[..., Any]] = {}
        self.connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_delay = 30.0
        self._method_sequence: list[str] = []
        self._method_index = 0
        self._fallback_start_index: Optional[int] = None
        self._last_method: Optional[str] = None
        self._last_status_key: Optional[tuple[Optional[str], bool]] = None
        self._status_last_change_ts: Optional[float] = None
        self._last_wifi_check = 0.0
        self._wifi_check_interval = 5.0
        self._last_promotion_check = 0.0
        self._promotion_interval = 15.0
        self._request_queue: deque[dict[str, Any]] = deque()
        self._queue_lock = threading.Lock()
        self._processing_request = False

    def _load_priority_methods(self) -> list[str]:
        config_path = Path(__file__).resolve().parent / "comms_priority.json"
        if not config_path.exists():
            return ["meshtastic"]
        try:
            payload = json.loads(config_path.read_text())
            methods = (
                payload.get("priority_methods") if isinstance(payload, dict) else None
            )
            if isinstance(methods, list) and methods:
                return [str(m) for m in methods]
        except Exception as exc:
            LOGGER.warning("Failed to load comms priority config: %s", exc)
        return ["meshtastic"]

    def _resolve_enabled_methods(
        self, comms_cfg: Dict[str, Any]
    ) -> Optional[list[str]]:
        enabled = comms_cfg.get("enabled_methods") or comms_cfg.get("methods")
        if isinstance(enabled, list) and enabled:
            return [str(m) for m in enabled]
        legacy = comms_cfg.get("method") or comms_cfg.get("transport")
        if legacy:
            return [str(legacy)]
        return None

    def _iter_methods(self) -> list[str]:
        if self.enabled_methods:
            filtered = [m for m in self.priority_methods if m in self.enabled_methods]
            if not filtered:
                LOGGER.error(
                    "No enabled comms methods match priority list: enabled=%s priority=%s",
                    self.enabled_methods,
                    self.priority_methods,
                )
            return filtered
        return list(self.priority_methods)

    def _register_functions(self) -> None:
        self.functions.clear()
        if not self.connected or not self.client:
            return
        for name, func in FUNCTION_REGISTRY.items():
            self.functions[name] = lambda _f=func, **kwargs: _f(self.client, **kwargs)

    def _init_bridge(self, start_index: int = 0) -> None:
        self.client = None
        self.connected = False

        self._method_sequence = self._iter_methods()
        self._method_index = max(0, start_index)

        initialized = False
        for idx, method in enumerate(
            self._method_sequence[start_index:], start=start_index
        ):
            if method == "wifi":
                initialized = self._init_wifi()
            elif method == "meshtastic":
                initialized = self._init_meshtastic()
            else:
                LOGGER.error("Unknown comms method '%s'", method)
                continue

            if initialized:
                self._method_index = idx
                break

        if not initialized:
            LOGGER.error("No comms method initialized successfully")
            return

        # Register callable functions for other modules (client injected)
        # Only register functions if we successfully connected
        if self.connected and self.client:
            self._register_functions()
            self._reconnect_attempts = 0
            self._publish_method_change()
            LOGGER.info("Comms bridge initialized (method=%s)", self.method)

    def _publish_method_change(self, *, force: bool = False) -> None:
        if not self.method:
            return
        if not force and self.method == self._last_method:
            return
        self._last_method = self.method
        self.bus.publish(
            "comms.method_changed",
            {"method": self.method, "timestamp": time.time()},
        )
        self._publish_status()

    def _build_status_payload(self, request_id: Optional[str] = None) -> dict[str, Any]:
        transport: dict[str, Any] = {}
        if self.method == "wifi":
            transport = {
                "interface": self.wifi_config.get("interface"),
                "ssid": self.wifi_config.get("ssid"),
            }
        elif self.method == "meshtastic":
            transport = {
                "radio_port": self.radio_port,
                "gateway_node_id": self.gateway_node_id,
                "mode": self.mode,
                "simulated": self.simulated,
            }
        # last_change_ts will be None initially until first status change
        payload: dict[str, Any] = {
            "method": self.method,
            "connected": self.connected,
            "last_change_ts": self._status_last_change_ts,
            "transport": transport,
            "timestamp": time.time(),
        }
        if request_id:
            payload["request_id"] = request_id
        return payload

    def _publish_status(
        self, *, force: bool = False, request_id: Optional[str] = None
    ) -> None:
        status_key = (self.method, self.connected)
        changed = status_key != self._last_status_key
        if changed:
            self._status_last_change_ts = time.time()
            self._last_status_key = status_key
        if force or request_id or changed:
            self.bus.publish(
                "comms.status", self._build_status_payload(request_id=request_id)
            )

    def _build_wifi_client(self):
        atlas_cfg = (
            self.config.get("atlas", {}) if isinstance(self.config, dict) else {}
        )
        base_url = atlas_cfg.get("base_url")
        api_token = atlas_cfg.get("api_token")

        # Validate base_url before passing to build_wifi_client
        if not base_url or not isinstance(base_url, str) or not base_url.strip():
            LOGGER.error("WiFi comms requires a valid atlas.base_url in configuration")
            raise RuntimeError(
                "WiFi comms requires a valid atlas.base_url in configuration"
            )

        return build_wifi_client(
            base_url=base_url,
            api_token=api_token,
            wifi_config=self.wifi_config,
        )

    def _init_wifi(self) -> bool:
        try:
            self.client = self._build_wifi_client()
        except Exception as exc:
            LOGGER.error("Failed to initialize wifi comms: %s", exc)
            return False

        self.method = "wifi"
        self.connected = True
        self._last_wifi_check = time.time()
        return True

    def _init_meshtastic(self) -> bool:
        try:
            self.client = build_meshtastic_client(
                simulated=self.simulated,
                radio_port=self.radio_port,
                gateway_node_id=self.gateway_node_id,
                mode=self.mode,
                spool_path=self.spool_path,
            )
        except Exception as exc:
            LOGGER.error("Failed to initialize meshtastic comms: %s", exc)
            return False

        self.method = "meshtastic"
        self.connected = True
        return True

    def start(self) -> None:
        self._logger.info("Starting Comms Manager (simulated=%s)", self.simulated)
        self.running = True
        self._init_bridge()

        # Subscribe to outgoing requests if needed later
        self.bus.subscribe("comms.send_message", self._handle_send_request)
        self.bus.subscribe("comms.request", self._handle_bus_request)
        self.bus.subscribe("comms.get_status", self._handle_get_status)
        self.bus.subscribe("os.boot_complete", self._handle_boot_complete)

        self._publish_status(force=True)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._logger.info("Stopping Comms Manager")
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        # Close radio if present
        if (
            self.method == "meshtastic"
            and self.client
            and hasattr(self.client.transport.radio, "close")
        ):
            try:
                self.client.transport.radio.close()
            except Exception:
                pass

    def _loop(self):
        """Main comms loop - polls for incoming messages and handles reconnection."""
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.running:
            if not self.client or not self.connected:
                self._attempt_reconnection()
                time.sleep(1)
                continue

            if self.method == "wifi":
                now = time.time()
                if now - self._last_wifi_check >= self._wifi_check_interval:
                    self._last_wifi_check = now
                    try:
                        if not self.client.is_connected(
                            self.wifi_config.get("interface")
                        ):
                            self._handle_disconnection()
                            continue
                        if not self.client.has_connectivity():
                            self.client.mark_bad_current(
                                self.wifi_config.get("interface")
                            )
                            self.client.disconnect(self.wifi_config.get("interface"))
                            self._handle_disconnection()
                            continue
                    except Exception as exc:
                        LOGGER.warning("WiFi connection check failed: %s", exc)
                        self._handle_disconnection()
                        continue

            if self._should_promote():
                if self._promote_to_preferred():
                    continue

            request = self._dequeue_request()
            if request:
                self._processing_request = True
                try:
                    self._process_request(request)
                finally:
                    self._processing_request = False
                if self._should_promote():
                    self._promote_to_preferred()
                continue

            if self.method != "meshtastic":
                time.sleep(1)
                continue

            try:
                # Poll for incoming messages
                sender, message = self.client.transport.receive_message(timeout=0.5)

                if message:
                    consecutive_errors = 0
                    # Publish received message to bus
                    self.bus.publish(
                        "comms.message_received",
                        {
                            "sender": sender,
                            "message_id": message.id,
                            "command": message.command,
                            "type": message.type,
                            "data": message.data or {},
                            "correlation_id": message.correlation_id,
                            "timestamp": time.time(),
                        },
                    )
                    LOGGER.debug(
                        "Received message: sender=%s, command=%s, type=%s",
                        sender,
                        message.command,
                        message.type,
                    )
                else:
                    # No message received, process outbox for pending sends
                    if self.client and self.client.transport:
                        try:
                            self.client.transport.process_outbox()
                        except Exception as exc:
                            LOGGER.debug("Error processing outbox: %s", exc)

            except Exception as exc:
                consecutive_errors += 1
                LOGGER.warning(
                    "Error receiving message (consecutive errors: %d): %s",
                    consecutive_errors,
                    exc,
                )

                # If we hit too many consecutive errors, mark as disconnected
                if consecutive_errors >= max_consecutive_errors:
                    LOGGER.error(
                        "Too many consecutive errors, marking connection as lost"
                    )
                    self._handle_disconnection()
                    consecutive_errors = 0
                else:
                    time.sleep(0.1)  # Brief pause before retry

    def _handle_disconnection(self):
        """Handle transport disconnection."""
        if self.connected:
            self.connected = False
            self.bus.publish("comms.connection_lost", {"timestamp": time.time()})
            self._publish_status()
            LOGGER.warning("Comms connection lost")
            next_index = self._method_index + 1
            if self._method_sequence and next_index < len(self._method_sequence):
                self._fallback_start_index = next_index
            else:
                self._fallback_start_index = 0

    def _attempt_reconnection(self):
        """Attempt to reconnect to the radio with exponential backoff."""
        if not self.running:
            return

        # Calculate exponential backoff delay (1s, 2s, 4s, 8s, ... up to max)
        delay = min(2.0**self._reconnect_attempts, self._max_reconnect_delay)

        if self._reconnect_attempts == 0:
            LOGGER.info("Attempting to reconnect comms...")
        else:
            LOGGER.info(
                "Retrying comms reconnection (attempt %d, delay %.1fs)...",
                self._reconnect_attempts + 1,
                delay,
            )
            time.sleep(delay)

        try:
            # Try to reinitialize the bridge
            start_index = self._fallback_start_index or 0
            self._init_bridge(start_index=start_index)

            # If we successfully reconnected
            if self.client and self.connected:
                if self._reconnect_attempts > 0:
                    LOGGER.info("Comms reconnection successful")
                    self.bus.publish(
                        "comms.connection_restored", {"timestamp": time.time()}
                    )
                self._publish_status()
                self._reconnect_attempts = 0
                self._fallback_start_index = None
            else:
                self._reconnect_attempts += 1
                if self._fallback_start_index and self._fallback_start_index != 0:
                    self._fallback_start_index = 0

        except Exception as exc:
            LOGGER.warning("Reconnection attempt failed: %s", exc)
            self._reconnect_attempts += 1
            self.connected = False

    def _dequeue_request(self) -> Optional[dict[str, Any]]:
        with self._queue_lock:
            if self._request_queue:
                return self._request_queue.popleft()
        return None

    def _process_request(self, data: dict[str, Any]) -> None:
        if not data:
            return
        func_name = data.get("function")
        args = data.get("args") or {}
        req_id = data.get("request_id") or data.get("id")

        if not func_name:
            LOGGER.warning("comms.request missing function name")
            return
        func = self.functions.get(func_name)
        if func is None:
            LOGGER.warning("Unknown comms function requested: %s", func_name)
            return
        if self.client is None:
            LOGGER.warning("Comms client not initialized; cannot handle %s", func_name)
            return

        start = time.time()
        try:
            result = func(**args)
            elapsed = time.time() - start
            self.bus.publish(
                "comms.response",
                {
                    "function": func_name,
                    "request_id": req_id,
                    "ok": True,
                    "result": (
                        result.to_dict() if hasattr(result, "to_dict") else result
                    ),
                    "elapsed": elapsed,
                },
            )
        except Exception as exc:
            error = exc
            if not self.connected:
                prev_method = self.method
                self._handle_disconnection()
                self._attempt_reconnection()
                if self.connected and self.method != prev_method:
                    retry_func = self.functions.get(func_name)
                    if retry_func is not None:
                        try:
                            result = retry_func(**args)
                            elapsed = time.time() - start
                            self.bus.publish(
                                "comms.response",
                                {
                                    "function": func_name,
                                    "request_id": req_id,
                                    "ok": True,
                                    "result": (
                                        result.to_dict()
                                        if hasattr(result, "to_dict")
                                        else result
                                    ),
                                    "elapsed": elapsed,
                                },
                            )
                            return
                        except Exception as retry_exc:
                            error = retry_exc
            elapsed = time.time() - start
            LOGGER.exception("Error handling comms function %s: %s", func_name, error)
            self.bus.publish(
                "comms.response",
                {
                    "function": func_name,
                    "request_id": req_id,
                    "ok": False,
                    "error": str(error),
                    "elapsed": elapsed,
                },
            )

    def _should_promote(self) -> bool:
        if not self.connected or not self._method_sequence:
            return False
        if self.method == self._method_sequence[0]:
            return False
        if self._processing_request:
            return False
        if not self._meshtastic_outbox_empty():
            return False
        now = time.time()
        if now - self._last_promotion_check < self._promotion_interval:
            return False
        self._last_promotion_check = now
        return True

    def _promote_to_preferred(self) -> bool:
        preferred = self._method_sequence[0] if self._method_sequence else None
        if preferred == "wifi":
            if not self._meshtastic_outbox_empty():
                return False
            try:
                wifi_client = self._build_wifi_client()
            except Exception as exc:
                LOGGER.info("Preferred wifi not available: %s", exc)
                return False
            if not wifi_client.is_connected(self.wifi_config.get("interface")):
                return False
            if (
                self.method == "meshtastic"
                and self.client
                and hasattr(self.client.transport.radio, "close")
            ):
                try:
                    self.client.transport.radio.close()
                except Exception:
                    # Ignore errors during cleanup - we're switching transports anyway
                    # and the old transport will be garbage collected
                    pass
            self.client = wifi_client
            self.method = "wifi"
            self.connected = True
            self._method_index = 0
            self._register_functions()
            self._publish_method_change()
            LOGGER.info("Promoted comms to wifi")
            return True
        return False

    def _meshtastic_outbox_empty(self) -> bool:
        if self.method != "meshtastic":
            return True
        transport = getattr(self.client, "transport", None)
        spool = getattr(transport, "spool", None) if transport else None
        depth = None
        if spool and hasattr(spool, "depth"):
            try:
                depth = spool.depth()
            except Exception:
                depth = None
        if depth is None:
            return True
        return depth == 0

    def _handle_send_request(self, data):
        """Handle request to send message to outside world."""
        dest = data.get("dest")
        payload = data.get("payload")
        LOGGER.info("Stub send request to %s: %s", dest, payload)
        # Hook for future outbound routing

    def _handle_bus_request(self, data):
        """Enqueue a comms function call for ordered processing."""
        if not data:
            return
        with self._queue_lock:
            self._request_queue.append(data)

    def _handle_get_status(self, data):
        request_id = None
        if isinstance(data, dict):
            request_id = data.get("request_id")
        self._publish_status(force=True, request_id=request_id)

    def _handle_boot_complete(self, _data):
        """Handle os.boot_complete event."""
        self._publish_method_change(force=True)
