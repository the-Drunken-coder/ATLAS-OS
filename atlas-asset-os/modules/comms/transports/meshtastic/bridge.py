import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

LOGGER = logging.getLogger("modules.comms.meshtastic")

# Bridge imports (local source path wiring)
# Repo root is parents[5] for .../ATLAS_ASSET_OS/modules/comms/transports/meshtastic/bridge.py
_ROOT = Path(__file__).resolve().parents[5]
_BRIDGE_SRC = _ROOT / "Atlas_Command" / "connection_packages" / "atlas_meshtastic_bridge" / "src"
if str(_BRIDGE_SRC) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_SRC))

from atlas_meshtastic_bridge.cli import build_radio  # type: ignore  # noqa: E402
from atlas_meshtastic_bridge.client import MeshtasticClient  # type: ignore[import-not-found]  # noqa: E402
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


def build_meshtastic_client(
    *,
    simulated: bool,
    radio_port: Optional[str],
    gateway_node_id: str,
    mode: str,
    spool_path: str,
) -> MeshtasticClient:
    """Build a Meshtastic client for the comms module."""
    profile: Dict[str, Any] = {}
    try:
        profile = load_mode_profile(mode)
        LOGGER.info("Loaded mode profile %s for comms", mode)
    except Exception as exc:
        LOGGER.warning("Failed to load mode profile %s: %s (using defaults)", mode, exc)
        profile = {}

    mode_rel = profile.get("reliability_method") if isinstance(profile, dict) else None
    reliability = strategy_from_name(mode_rel)
    if mode_rel:
        os.environ["ATLAS_RELIABILITY_METHOD"] = str(mode_rel)

    port = radio_port
    if not simulated and not port:
        port = _find_available_port()
        if not port:
            raise RuntimeError("No radio port available for comms")
        LOGGER.info("Comms discovered radio port: %s", port)

    node_id = _read_node_id(port) if (port and not simulated) else None
    if node_id:
        LOGGER.info("Comms using radio node ID: %s", node_id)

    transport_kwargs: Dict[str, Any] = {}
    if isinstance(profile, dict):
        transport_kwargs = profile.get("transport", {}) or {}

    radio = build_radio(simulated, port, node_id)
    transport = MeshtasticTransport(
        radio,
        spool_path=spool_path,
        reliability=reliability,
        enable_spool=True,
        **transport_kwargs,
    )
    return MeshtasticClient(transport, gateway_node_id=gateway_node_id)
