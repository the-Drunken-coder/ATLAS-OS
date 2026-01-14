import sys
import os
import json
import logging
from pathlib import Path
from typing import Optional

# --- Path Setup to use LOCAL source code ---
# We assume this OS is running from Atlas_Tool_OSs/Gateway_OS
# And the source code is in Atlas_Command/connection_packages/...

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1] # Up to ATLAS root

# Paths to the local packages
BRIDGE_SRC = REPO_ROOT / "Atlas_Command" / "connection_packages" / "atlas_meshtastic_bridge" / "src"
HTTP_CLIENT_SRC = REPO_ROOT / "Atlas_Command" / "connection_packages" / "atlas_asset_http_client_python" / "src"

# Verify paths exist
if not BRIDGE_SRC.exists():
    print(f"Error: Bridge source not found at {BRIDGE_SRC}")
    sys.exit(1)
if not HTTP_CLIENT_SRC.exists():
    print(f"Error: HTTP Client source not found at {HTTP_CLIENT_SRC}")
    sys.exit(1)

# Add to sys.path
sys.path.insert(0, str(BRIDGE_SRC))
sys.path.insert(0, str(HTTP_CLIENT_SRC))

print(f"Added to sys.path: \n - {BRIDGE_SRC}\n - {HTTP_CLIENT_SRC}")

# --- Import Bridge CLI ---
try:
    from atlas_meshtastic_bridge.cli import main as bridge_main
    from atlas_meshtastic_bridge.modes import load_mode_profile
except ImportError as e:
    print(f"Failed to import bridge: {e}")
    sys.exit(1)

try:
    from meshtastic import serial_interface, util as meshtastic_util  # type: ignore
except Exception:
    serial_interface = None  # type: ignore
    meshtastic_util = None  # type: ignore

try:
    from serial.tools import list_ports  # type: ignore
except Exception:
    list_ports = None  # type: ignore

def load_config():
    try:
        config_path = CURRENT_DIR / "config.json"
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load config.json: {e}")
        return {}


def _discover_radio_port() -> Optional[str]:
    """Best-effort radio port discovery using meshtastic util or pyserial."""
    ports = []
    if meshtastic_util:
        try:
            ports = meshtastic_util.findPorts() or []
        except Exception as exc:  # pragma: no cover - hardware specific
            logging.warning("meshtastic util port discovery failed: %s", exc)
    if not ports and list_ports:
        try:
            ports = [p.device for p in list_ports.comports()]
        except Exception as exc:  # pragma: no cover - hardware specific
            logging.warning("pyserial port discovery failed: %s", exc)
    if not ports:
        return None
    # Normalize potential dict entries from meshtastic util
    first = ports[0]
    if isinstance(first, dict) and "device" in first:
        return str(first["device"])
    return str(first)


def _read_radio_node_id(port: str) -> Optional[str]:
    """Attempt to read the radio's existing node/user ID."""
    if serial_interface is None:
        return None
    try:
        iface = serial_interface.SerialInterface(port)
        info = getattr(iface, "getMyNodeInfo", lambda: {})() or {}
        iface.close()
        user = info.get("user") if isinstance(info, dict) else None
        node_id = user.get("id") if isinstance(user, dict) else None
        return str(node_id) if node_id else None
    except Exception as exc:  # pragma: no cover - hardware specific
        logging.warning("Could not read node ID from radio on %s: %s", port, exc)
        return None


def _apply_modem_preset(preset_name: str, gateway_port: str, simulate: bool) -> None:
    """Best-effort apply a Meshtastic modem preset to the gateway radio."""
    if simulate:
        logging.info("Simulation enabled; skipping modem preset change (%s)", preset_name)
        return
    try:
        from meshtastic import config_pb2, serial_interface
    except ImportError as exc:  # pragma: no cover - hardware-only path
        logging.warning("meshtastic not available; cannot set modem preset %s: %s", preset_name, exc)
        return

    preset_map = {
        "LONG_FAST": config_pb2.Config.LoRaConfig.ModemPreset.LONG_FAST,
        "LONG_SLOW": config_pb2.Config.LoRaConfig.ModemPreset.LONG_SLOW,
        "LONG_MODERATE": config_pb2.Config.LoRaConfig.ModemPreset.LONG_MODERATE,
        "VERY_LONG_SLOW": config_pb2.Config.LoRaConfig.ModemPreset.VERY_LONG_SLOW,
        "MEDIUM_FAST": config_pb2.Config.LoRaConfig.ModemPreset.MEDIUM_FAST,
        "MEDIUM_SLOW": config_pb2.Config.LoRaConfig.ModemPreset.MEDIUM_SLOW,
        "SHORT_FAST": config_pb2.Config.LoRaConfig.ModemPreset.SHORT_FAST,
        "SHORT_SLOW": config_pb2.Config.LoRaConfig.ModemPreset.SHORT_SLOW,
        "SHORT_TURBO": config_pb2.Config.LoRaConfig.ModemPreset.SHORT_TURBO,
    }
    preset_value = preset_map.get(str(preset_name).upper())
    if preset_value is None:
        logging.warning("Unknown modem preset %s; skipping preset change", preset_name)
        return
    try:
        iface = serial_interface.SerialInterface(gateway_port)
        cfg = iface.localNode.localConfig
        cfg.lora.modem_preset = preset_value
        iface.localNode.writeConfig("lora")
        logging.info("Set gateway radio (%s) to preset %s", gateway_port, preset_name)
        iface.close()
    except Exception as exc:  # pragma: no cover - hardware only
        logging.warning("Failed to set preset %s on %s: %s", preset_name, gateway_port, exc)

def run():
    config = load_config()

    # Configure logging early
    log_level = str(config.get("log_level", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.info("Loaded config from %s: %s", CURRENT_DIR / "config.json", {k: v for k, v in config.items() if k != "api_token"})

    # If not simulating, try to auto-detect radio port and node ID.
    radio_port = config.get("radio_port")
    if not config.get("simulate_radio"):
        if not radio_port:
            radio_port = _discover_radio_port()
            if radio_port:
                logging.info("Discovered radio port: %s", radio_port)
                config["radio_port"] = radio_port
            else:
                logging.warning("No radio port found; set radio_port in config.json")
        # Prefer the radio's existing node ID if available
        if radio_port:
            node_id = _read_radio_node_id(radio_port)
            if node_id:
                placeholder = config.get("gateway_node_id")
                if not placeholder or placeholder == "gateway-001":
                    logging.info("Using radio node ID as gateway_node_id: %s", node_id)
                    config["gateway_node_id"] = node_id
            else:
                logging.info("Radio node ID not read; keeping configured gateway_node_id: %s", config.get("gateway_node_id"))
        else:
            logging.warning("Skipping node ID read because no radio port is set")
    else:
        logging.info("simulate_radio is true; skipping radio discovery and node ID read")

    # Load mode profile for reliability/modem preset defaults
    mode_name = config.get("mode") or "general"
    profile = {}
    try:
        profile = load_mode_profile(mode_name)
        logging.info("Loaded mode profile %s", mode_name)
    except Exception as exc:
        logging.warning("Failed to load mode profile %s: %s", mode_name, exc)
        profile = {}

    # Apply reliability method via env (transport reads ATLAS_RELIABILITY_METHOD)
    mode_rel = profile.get("reliability_method") if isinstance(profile, dict) else None
    if mode_rel:
        os.environ["ATLAS_RELIABILITY_METHOD"] = str(mode_rel)
        logging.info("Using reliability method from mode: %s", mode_rel)

    # Apply modem preset if provided
    modem_preset = profile.get("modem_preset") if isinstance(profile, dict) else None
    if modem_preset and config.get("radio_port"):
        _apply_modem_preset(modem_preset, config["radio_port"], config.get("simulate_radio"))

    # Construct arguments for the bridge CLI
    # The bridge uses argparse, so we can mock sys.argv or call the logic directly if exposed.
    # checking cli.py, it calls parse_args() which uses sys.argv. 
    # So we will inject sys.argv.
    
    argv = ["master.py", "--mode", "gateway"]
    
    if config.get("gateway_node_id"):
        argv.extend(["--gateway-node-id", config["gateway_node_id"]])
        
    if config.get("api_base_url"):
        argv.extend(["--api-base-url", config["api_base_url"]])
        
    if config.get("api_token"):
        argv.extend(["--api-token", config["api_token"]])

    if config.get("simulate_radio"):
        argv.append("--simulate-radio")
        
    if config.get("radio_port"):
        argv.extend(["--radio-port", config["radio_port"]])
    else:
        logging.warning("No radio_port configured or discovered; the bridge may fail to start")

    # Disable metrics HTTP server (port 9700) per request
    argv.append("--disable-metrics")

    logging.info("Final gateway arguments: %s", argv)

    print(f"Launching Gateway with args: {argv}")
    
    sys.argv = argv
    bridge_main()

if __name__ == "__main__":
    run()
