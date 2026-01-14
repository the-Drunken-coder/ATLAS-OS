import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Bridge imports (local source path wiring)
_BASE_DIR = Path(__file__).resolve().parents[2]  # BasePlate_OS
# Repo root is parents[4] for .../BasePlate_OS/modules/comms/manager.py
_ROOT = Path(__file__).resolve().parents[4]
_BRIDGE_SRC = _ROOT / "Atlas_Command" / "connection_packages" / "atlas_meshtastic_bridge" / "src"
if str(_BRIDGE_SRC) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_SRC))
# Ensure BasePlate_OS root is on path for module_base import
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from module_base import ModuleBase  # noqa: E402

from atlas_meshtastic_bridge.cli import build_radio  # type: ignore  # noqa: E402
from atlas_meshtastic_bridge.client import MeshtasticClient  # type: ignore  # noqa: E402
from atlas_meshtastic_bridge.modes import load_mode_profile  # type: ignore  # noqa: E402
from atlas_meshtastic_bridge.reliability import strategy_from_name  # type: ignore  # noqa: E402
from atlas_meshtastic_bridge.transport import MeshtasticTransport  # type: ignore  # noqa: E402

try:
    from meshtastic import util as meshtastic_util  # type: ignore
except Exception:
    meshtastic_util = None  # type: ignore

try:
    from serial.tools import list_ports  # type: ignore
except Exception:
    list_ports = None  # type: ignore

from .functions import FUNCTION_REGISTRY

LOGGER = logging.getLogger("modules.comms")


def _candidate_ports() -> list[str]:
    seen: list[str] = []
    if meshtastic_util:
        try:
            ports = meshtastic_util.findPorts() or []
            for p in ports:
                if isinstance(p, dict) and "device" in p:
                    seen.append(str(p["device"]))
                else:
                    seen.append(str(p))
        except Exception as exc:
            LOGGER.warning("Meshtastic port discovery failed: %s", exc)
    if list_ports:
        try:
            for p in list_ports.comports():
                if p.device not in seen:
                    seen.append(p.device)
        except Exception as exc:
            LOGGER.warning("pyserial port discovery failed: %s", exc)
    return seen


def _find_available_port() -> Optional[str]:
    """Return the first port we can open, skipping busy ones."""
    try:
        from meshtastic import serial_interface  # type: ignore
    except Exception:
        serial_interface = None  # type: ignore
    for port in _candidate_ports():
        if serial_interface is None:
            return port
        try:
            iface = serial_interface.SerialInterface(port)
            iface.close()
            return port
        except Exception as exc:
            LOGGER.warning("Port %s busy/unavailable (%s), trying next", port, exc)
            continue
    return None


def _read_node_id(port: str) -> Optional[str]:
    try:
        from meshtastic import serial_interface  # type: ignore
    except Exception:
        return None
    try:
        iface = serial_interface.SerialInterface(port)
        info = getattr(iface, "getMyNodeInfo", lambda: {})() or {}
        user = info.get("user") if isinstance(info, dict) else None
        node_id = user.get("id") if isinstance(user, dict) else None
        iface.close()
        return str(node_id) if node_id else None
    except Exception as exc:
        LOGGER.warning("Could not read node ID from %s: %s", port, exc)
        return None


class CommsManager(ModuleBase):
    """Communications manager for Meshtastic radio bridge."""
    
    MODULE_NAME = "comms"
    MODULE_VERSION = "1.0.0"
    DEPENDENCIES: List[str] = []  # No dependencies, starts first
    
    def __init__(self, bus, config):
        super().__init__(bus, config)
        self._thread: Optional[threading.Thread] = None

        comms_cfg = self.get_module_config()
        self.simulated = bool(comms_cfg.get("simulated", False))
        self.gateway_node_id = comms_cfg.get("gateway_node_id") or "gateway"
        self.radio_port = comms_cfg.get("radio_port")
        self.mode = comms_cfg.get("mode") or "general"
        self.spool_path = os.path.expanduser(comms_cfg.get("spool_path", "~/.baseplate_comm_spool.json"))

        self.client: Optional[MeshtasticClient] = None
        self.functions: Dict[str, Callable[..., Any]] = {}
        self.connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_delay = 30.0

    def _init_bridge(self) -> None:
        # Load mode profile for reliability/transport defaults
        profile = {}
        try:
            profile = load_mode_profile(self.mode)
            LOGGER.info("Loaded mode profile %s for comms", self.mode)
        except Exception as exc:
            LOGGER.warning("Failed to load mode profile %s: %s (using defaults)", self.mode, exc)
            profile = {}

        mode_rel = profile.get("reliability_method") if isinstance(profile, dict) else None
        reliability = strategy_from_name(mode_rel)
        if mode_rel:
            os.environ["ATLAS_RELIABILITY_METHOD"] = str(mode_rel)

        port = self.radio_port
        if not self.simulated and not port:
            port = _find_available_port()
            if not port:
                LOGGER.error("No radio port available for comms")
                return
            LOGGER.info("Comms discovered radio port: %s", port)

        node_id = _read_node_id(port) if (port and not self.simulated) else None
        if node_id:
            LOGGER.info("Comms using radio node ID: %s", node_id)

        transport_kwargs: Dict[str, Any] = {}
        if isinstance(profile, dict):
            transport_kwargs = profile.get("transport", {}) or {}

        radio = build_radio(self.simulated, port, node_id)
        transport = MeshtasticTransport(
            radio,
            spool_path=self.spool_path,
            reliability=reliability,
            enable_spool=True,
            **transport_kwargs,
        )
        self.client = MeshtasticClient(transport, gateway_node_id=self.gateway_node_id)

        # Register callable functions for other modules (client injected)
        for name, func in FUNCTION_REGISTRY.items():
            self.functions[name] = lambda _f=func, **kwargs: _f(self.client, **kwargs)
        self.connected = True
        self._reconnect_attempts = 0
        LOGGER.info("Comms bridge initialized (simulated=%s, gateway=%s)", self.simulated, self.gateway_node_id)

    def start(self) -> None:
        self._logger.info("Starting Comms Manager (simulated=%s)", self.simulated)
        self.running = True
        self._init_bridge()

        # Subscribe to outgoing requests if needed later
        self.bus.subscribe("comms.send_message", self._handle_send_request)
        self.bus.subscribe("comms.request", self._handle_bus_request)

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._logger.info("Stopping Comms Manager")
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        # Close radio if present
        if self.client and hasattr(self.client.transport.radio, "close"):
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
                LOGGER.warning("Error receiving message (consecutive errors: %d): %s", consecutive_errors, exc)
                
                # If we hit too many consecutive errors, mark as disconnected
                if consecutive_errors >= max_consecutive_errors:
                    LOGGER.error("Too many consecutive errors, marking connection as lost")
                    self._handle_disconnection()
                    consecutive_errors = 0
                else:
                    time.sleep(0.1)  # Brief pause before retry
    
    def _handle_disconnection(self):
        """Handle radio disconnection."""
        if self.connected:
            self.connected = False
            self.bus.publish("comms.connection_lost", {"timestamp": time.time()})
            LOGGER.warning("Radio connection lost")
    
    def _attempt_reconnection(self):
        """Attempt to reconnect to the radio with exponential backoff."""
        if not self.running:
            return
        
        # Calculate exponential backoff delay (1s, 2s, 4s, 8s, ... up to max)
        delay = min(2.0 ** self._reconnect_attempts, self._max_reconnect_delay)
        
        if self._reconnect_attempts == 0:
            LOGGER.info("Attempting to reconnect radio...")
        else:
            LOGGER.info("Retrying radio reconnection (attempt %d, delay %.1fs)...", self._reconnect_attempts + 1, delay)
            time.sleep(delay)
        
        try:
            # Try to reinitialize the bridge
            old_client = self.client
            self._init_bridge()
            
            # If we successfully reconnected
            if self.client and self.connected:
                if self._reconnect_attempts > 0:
                    LOGGER.info("Radio reconnection successful")
                    self.bus.publish("comms.connection_restored", {"timestamp": time.time()})
                self._reconnect_attempts = 0
            else:
                self._reconnect_attempts += 1
                
        except Exception as exc:
            LOGGER.warning("Reconnection attempt failed: %s", exc)
            self._reconnect_attempts += 1
            self.connected = False

    def _handle_send_request(self, data):
        """Handle request to send message to outside world."""
        dest = data.get("dest")
        payload = data.get("payload")
        LOGGER.info("Stub send request to %s: %s", dest, payload)
        # Hook for future outbound routing

    def _handle_bus_request(self, data):
        """Dispatch a comms function call from the bus.

        Expected payload:
            {
              "function": "list_entities",
              "args": {...},            # optional, defaults to {}
              "request_id": "abc123"    # optional correlation id
            }
        """
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
            LOGGER.warning("Meshtastic client not initialized; cannot handle %s", func_name)
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
                    "result": result.to_dict() if hasattr(result, "to_dict") else result,
                    "elapsed": elapsed,
                },
            )
        except Exception as exc:
            elapsed = time.time() - start
            LOGGER.exception("Error handling comms function %s: %s", func_name, exc)
            self.bus.publish(
                "comms.response",
                {
                    "function": func_name,
                    "request_id": req_id,
                    "ok": False,
                    "error": str(exc),
                    "elapsed": elapsed,
                },
            )
