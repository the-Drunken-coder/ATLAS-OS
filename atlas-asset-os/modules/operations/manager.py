import logging
import threading
import time
from typing import List, Optional


# Module base is in the same modules/ directory
from modules.module_base import ModuleBase  # noqa: E402

LOGGER = logging.getLogger("modules.operations")


class OperationsManager(ModuleBase):
    """Operations manager for message routing and heartbeat."""
    
    MODULE_NAME = "operations"
    MODULE_VERSION = "1.0.0"
    DEPENDENCIES: List[str] = ["comms"]  # Depends on comms module
    
    def __init__(self, bus, config):
        super().__init__(bus, config)
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._logger.info("Starting Operations Manager")
        self.running = True
        
        # Subscribe to bus events
        self.bus.subscribe("comms.message_received", self._handle_comms_message)
        
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
            # Check system health, manage state, etc.
            # Heartbeat at reduced frequency
            self.bus.publish("operations.heartbeat", {"status": "ok"})
            time.sleep(30)

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
