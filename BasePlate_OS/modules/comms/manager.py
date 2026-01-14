import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

LOGGER = logging.getLogger("modules.comms")

# Bridge imports (local source path wiring)
_BASE_DIR = Path(__file__).resolve().parents[2]  # BasePlate_OS
# Repo root is parents[4] for .../BasePlate_OS/modules/comms/manager.py
_ROOT = Path(__file__).resolve().parents[4]
_BRIDGE_SRC = _ROOT / "Atlas_Command" / "connection_packages" / "atlas_meshtastic_bridge" / "src"
if str(_BRIDGE_SRC) not in os.sys.path:
    os.sys.path.insert(0, str(_BRIDGE_SRC))

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


class CommsManager:
    def __init__(self, bus, config):
        self.bus = bus
        self.config = config
        self.running = False
        self._thread: Optional[threading.Thread] = None

        comms_cfg = config.get("modules", {}).get("comms", {})
        self.simulated = bool(comms_cfg.get("simulated", False))
        self.gateway_node_id = comms_cfg.get("gateway_node_id") or "gateway"
        self.radio_port = comms_cfg.get("radio_port")
        self.mode = comms_cfg.get("mode") or "general"
        self.spool_path = os.path.expanduser(comms_cfg.get("spool_path", "~/.baseplate_comm_spool.json"))

        self.client: Optional[MeshtasticClient] = None
        self.functions: Dict[str, Callable[..., Any]] = {}

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
        LOGGER.info("Comms bridge initialized (simulated=%s, gateway=%s)", self.simulated, self.gateway_node_id)

    def start(self):
        LOGGER.info("Starting Comms Manager (simulated=%s)", self.simulated)
        self.running = True
        self._init_bridge()

        # Subscribe to outgoing requests if needed later
        self.bus.subscribe("comms.send_message", self._handle_send_request)
        self.bus.subscribe("comms.request", self._handle_bus_request)

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        LOGGER.info("Stopping Comms Manager")
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
        """Main comms loop placeholder."""
        while self.running:
            time.sleep(1)

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
