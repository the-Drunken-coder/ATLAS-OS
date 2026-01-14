import logging
import threading
import time

LOGGER = logging.getLogger("modules.operations")

class OperationsManager:
    def __init__(self, bus, config):
        self.bus = bus
        self.config = config
        self.running = False
        self._thread = None

    def start(self):
        LOGGER.info("Starting Operations Manager")
        self.running = True
        
        # Subscribe to bus events
        self.bus.subscribe("comms.message_received", self._handle_comms_message)
        
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        LOGGER.info("Stopping Operations Manager")
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
            LOGGER.warning("Invalid message structure received: %s", data)
            return
        
        # Extract message fields
        msg_type = data.get("type", "unknown")
        command = data.get("command", "unknown")
        message_id = data.get("message_id", "unknown")
        msg_data = data.get("data", {})
        sender = data.get("sender")
        
        LOGGER.info(
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
            LOGGER.warning("Unknown message type '%s' received", msg_type)
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
