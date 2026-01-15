import logging
import threading
import time
from typing import List, Optional


# Module base is in the same modules/ directory
from modules.module_base import ModuleBase  # noqa: E402
from modules.operations.registration import register_asset  # noqa: E402

LOGGER = logging.getLogger("modules.operations")


class OperationsManager(ModuleBase):
    """Operations manager for message routing and heartbeat."""
    
    MODULE_NAME = "operations"
    MODULE_VERSION = "1.0.0"
    DEPENDENCIES: List[str] = ["comms"]  # Depends on comms module
    
    def __init__(self, bus, config):
        super().__init__(bus, config)
        self._thread: Optional[threading.Thread] = None
        ops_cfg = self.get_module_config()
        self._heartbeat_interval_s = float(ops_cfg.get("heartbeat_interval_s", 30.0))
        self._checkin_interval_default_s = float(ops_cfg.get("checkin_interval_s", 30.0))
        self._checkin_interval_wifi_s = float(ops_cfg.get("checkin_interval_wifi_s", 1.0))
        self._checkin_interval_mesh_s = float(ops_cfg.get("checkin_interval_mesh_s", 15.0))
        raw_payload = ops_cfg.get("checkin_payload") or {}
        allowed_keys = {"latitude", "longitude", "altitude_m", "speed_m_s", "heading_deg"}
        self._checkin_payload = {
            key: value for key, value in raw_payload.items() if key in allowed_keys and value is not None
        }
        self._last_heartbeat = 0.0
        self._last_checkin = 0.0
        self._checkin_disabled_logged = False
        self._current_method: Optional[str] = None
        self._current_checkin_interval_s = self._checkin_interval_default_s
        self._registration_started = False
        self._registration_complete = False
        self._checkin_payload_logged = False
        self._checkin_waiting_logged = False

    def start(self) -> None:
        self._logger.info("Starting Operations Manager")
        self.running = True
        
        # Subscribe to bus events
        self.bus.subscribe("comms.message_received", self._handle_comms_message)
        self.bus.subscribe("comms.method_changed", self._handle_method_changed)

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._logger.info("Stopping Operations Manager")
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self):
        """Main operations loop."""
        while self.running:
            now = time.time()

            # Heartbeat at reduced frequency
            if now - self._last_heartbeat >= self._heartbeat_interval_s:
                self.bus.publish("operations.heartbeat", {"status": "ok"})
                self._last_heartbeat = now

            # Periodic check-in to Atlas Command (disabled if interval <= 0)
            if self._current_checkin_interval_s > 0 and now - self._last_checkin >= self._current_checkin_interval_s:
                asset_cfg = self.config.get("atlas", {}).get("asset", {}) if isinstance(self.config, dict) else {}
                entity_id = asset_cfg.get("id")
                if not entity_id:
                    if not self._checkin_disabled_logged:
                        self._logger.warning("Check-in disabled: missing atlas.asset.id in config")
                        self._checkin_disabled_logged = True
                elif not self._registration_complete:
                    if not self._checkin_waiting_logged:
                        self._logger.info("Check-in waiting for asset registration to complete")
                        self._checkin_waiting_logged = True
                elif not self._checkin_payload:
                    if not self._checkin_payload_logged:
                        self._logger.warning("Check-in disabled: operations.checkin_payload is empty")
                        self._checkin_payload_logged = True
                else:
                    self.bus.publish(
                        "comms.request",
                        {
                            "function": "checkin_entity",
                            "args": {"entity_id": entity_id, **self._checkin_payload},
                            "request_id": f"checkin-{int(now * 1000)}",
                        },
                    )
                    self._last_checkin = now

            time.sleep(1)

    def _handle_comms_message(self, data):
        """Handle messages received from the outside world."""
        if not data or not isinstance(data, dict):
            self._logger.warning("Invalid message structure received: %s", data)
            return
        
        # Extract message fields
        msg_type = data.get("type", "unknown")
        command = data.get("command", "unknown")
        message_id = data.get("message_id", "unknown")
        msg_data = data.get("data", {})
        sender = data.get("sender")
        
        self._logger.info(
            "Received message via comms: sender=%s, type=%s, command=%s, id=%s",
            sender,
            msg_type,
            command,
            message_id[:8] if message_id != "unknown" else "unknown",
        )
        
        # Route message to appropriate topic based on type
        if msg_type == "request":
            # Incoming command/request
            self.bus.publish(
                "operations.command_received",
                {
                    "sender": sender,
                    "command": command,
                    "message_id": message_id,
                    "data": msg_data,
                    "timestamp": data.get("timestamp", time.time()),
                },
            )
        elif msg_type == "response":
            # Response to a previous request
            self.bus.publish(
                "operations.data_received",
                {
                    "sender": sender,
                    "command": command,
                    "message_id": message_id,
                    "data": msg_data,
                    "correlation_id": data.get("correlation_id"),
                    "timestamp": data.get("timestamp", time.time()),
                },
            )
        elif msg_type == "error":
            # Error message
            self.bus.publish(
                "operations.error_received",
                {
                    "sender": sender,
                    "command": command,
                    "message_id": message_id,
                    "data": msg_data,
                    "correlation_id": data.get("correlation_id"),
                    "timestamp": data.get("timestamp", time.time()),
                },
            )
        else:
            # Unknown type, log and publish to generic topic
            self._logger.warning("Unknown message type '%s' received", msg_type)
            self.bus.publish(
                "operations.message_received",
                {
                    "sender": sender,
                    "type": msg_type,
                    "command": command,
                    "message_id": message_id,
                    "data": msg_data,
                    "timestamp": data.get("timestamp", time.time()),
                },
            )

    def _handle_method_changed(self, data):
        if not isinstance(data, dict):
            return
        method = data.get("method")
        if not method or method == self._current_method:
            return
        
        self._current_method = method
        if method == "wifi":
            self._current_checkin_interval_s = self._checkin_interval_wifi_s
        elif method == "meshtastic":
            self._current_checkin_interval_s = self._checkin_interval_mesh_s
        else:
            self._current_checkin_interval_s = self._checkin_interval_default_s
        
        # Calculate appropriate next check-in time based on elapsed time and new interval
        now = time.time()
        elapsed_since_last = now - self._last_checkin
        
        # If the new interval is shorter and we've already exceeded it, check in immediately
        # Otherwise, preserve timing to avoid redundant check-ins
        if self._current_checkin_interval_s < elapsed_since_last:
            # Switching to faster method and already past the interval
            self._last_checkin = now - self._current_checkin_interval_s
        # else: keep _last_checkin as-is to maintain check-in cadence
        
        self._logger.info(
            "Comms method set to %s; check-in interval %.1fs",
            method,
            self._current_checkin_interval_s,
        )

        if not self._registration_started:
            self._registration_started = True

            def _register():
                self._registration_complete = register_asset(self.bus, self.config)

            threading.Thread(target=_register, daemon=True).start()
