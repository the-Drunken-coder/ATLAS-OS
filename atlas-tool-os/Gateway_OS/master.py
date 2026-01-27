import sys
import os
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import threading

# --- Path Setup to use LOCAL source code ---
# We assume this OS is running from Atlas_Client_Systems/Atlas_Tool_OSs/Gateway_OS
# And the source code is in Atlas_Client_SDKs/connection_packages/...

CURRENT_DIR = Path(__file__).resolve().parent


def find_repo_root(start: Path) -> Path:
    """Walk up parents to find the repo root (directory containing .git)."""
    for ancestor in [start] + list(start.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return start


REPO_ROOT = find_repo_root(CURRENT_DIR)

# Paths to the local packages
BRIDGE_SRC = (
    REPO_ROOT
    / "Atlas_Client_SDKs"
    / "connection_packages"
    / "atlas_meshtastic_bridge"
    / "src"
)
HTTP_CLIENT_SRC = (
    REPO_ROOT
    / "Atlas_Client_SDKs"
    / "connection_packages"
    / "atlas_asset_http_client_python"
    / "src"
)

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
except ImportError:
    serial_interface = None  # type: ignore
    meshtastic_util = None  # type: ignore

try:
    from serial.tools import list_ports  # type: ignore
except ImportError:
    list_ports = None  # type: ignore


class MessageLogger:
    """Logs sent and received messages to a text file."""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.lock = threading.Lock()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Create log file with header if it doesn't exist."""
        if not self.log_file.exists():
            with open(self.log_file, "w") as f:
                f.write("=" * 80 + "\n")
                f.write("Gateway Message Log\n")
                f.write(f"Started: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
    
    def _format_message_data(self, data: dict) -> str:
        """Format message data for logging (truncate if too long)."""
        if not data:
            return "{}"
        # Convert to JSON string, truncate if too long
        try:
            json_str = json.dumps(data, indent=2)
            if len(json_str) > 500:
                return json_str[:500] + "... (truncated)"
            return json_str
        except (TypeError, ValueError):
            # Handle non-serializable data gracefully
            return str(data)[:500]
    
    def log_received(self, sender: str, envelope):
        """Log a received message."""
        with self.lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] RECEIVED\n")
                    f.write(f"  From: {sender}\n")
                    f.write(f"  Message ID: {envelope.id}\n")
                    f.write(f"  Type: {envelope.type}\n")
                    f.write(f"  Command: {envelope.command}\n")
                    if envelope.correlation_id:
                        f.write(f"  Correlation ID: {envelope.correlation_id}\n")
                    if envelope.data:
                        f.write(f"  Data:\n{self._format_message_data(envelope.data)}\n")
                    f.write("\n")
            except Exception as e:
                logging.error("Failed to write to message log: %s", e)
    
    def log_sent(self, destination: str, envelope):
        """Log a sent message."""
        with self.lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] SENT\n")
                    f.write(f"  To: {destination}\n")
                    f.write(f"  Message ID: {envelope.id}\n")
                    f.write(f"  Type: {envelope.type}\n")
                    f.write(f"  Command: {envelope.command}\n")
                    if envelope.correlation_id:
                        f.write(f"  Correlation ID: {envelope.correlation_id}\n")
                    if envelope.data:
                        f.write(f"  Data:\n{self._format_message_data(envelope.data)}\n")
                    f.write("\n")
            except Exception as e:
                logging.error("Failed to write to message log: %s", e)
    
    def log_message_chunked(self, message_id: str, total_chunks: int, chunk_sizes: list[int], destination: str):
        """Log when a message is split into chunks."""
        with self.lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] MESSAGE CHUNKED\n")
                    f.write(f"  Message ID: {message_id}\n")
                    f.write(f"  Total Chunks: {total_chunks}\n")
                    f.write(f"  Total Size: {sum(chunk_sizes)} bytes\n")
                    f.write(f"  To: {destination}\n")
                    f.write(f"  Chunk Sizes: {chunk_sizes}\n")
                    f.write("\n")
            except Exception as e:
                logging.error("Failed to write to message log: %s", e)
    
    def log_chunk_sent(self, message_id: str, chunk_seq: int, total_chunks: int, chunk_size: int, destination: str):
        """Log when a single chunk is sent."""
        with self.lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] CHUNK SENT\n")
                    f.write(f"  Message ID: {message_id}\n")
                    f.write(f"  Chunk: {chunk_seq}/{total_chunks}\n")
                    f.write(f"  Size: {chunk_size} bytes\n")
                    f.write(f"  To: {destination}\n")
                    f.write("\n")
            except Exception as e:
                logging.error("Failed to write to message log: %s", e)
    
    def log_chunk_received(self, message_id: str, chunk_seq: int, total_chunks: int, chunk_size: int, sender: str):
        """Log when a single chunk is received."""
        with self.lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] CHUNK RECEIVED\n")
                    f.write(f"  Message ID: {message_id}\n")
                    f.write(f"  Chunk: {chunk_seq}/{total_chunks}\n")
                    f.write(f"  Size: {chunk_size} bytes\n")
                    f.write(f"  From: {sender}\n")
                    f.write("\n")
            except Exception as e:
                logging.error("Failed to write to message log: %s", e)
    
    def log_message_complete(self, message_id: str, total_chunks: int, direction: str, node: str):
        """Log when a message is fully transmitted or received."""
        with self.lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] MESSAGE COMPLETE ({direction.upper()})\n")
                    f.write(f"  Message ID: {message_id}\n")
                    f.write(f"  Total Chunks: {total_chunks}\n")
                    f.write(f"  {'To' if direction == 'sent' else 'From'}: {node}\n")
                    f.write("\n")
            except Exception as e:
                logging.error("Failed to write to message log: %s", e)


# Global message logger instance (will be initialized in run())
_message_logger: Optional[MessageLogger] = None


def _patch_transport_for_logging():
    """Patch the MeshtasticTransport class to add message and chunk-level logging."""
    try:
        from atlas_meshtastic_bridge.transport import MeshtasticTransport, RadioInterface
        from atlas_meshtastic_bridge.message import MessageEnvelope, chunk_envelope
        
        # Store original methods
        original_send = MeshtasticTransport.send_message
        original_receive = MeshtasticTransport.receive_message
        original_enqueue = MeshtasticTransport.enqueue
        original_get_chunks = MeshtasticTransport._get_or_create_chunks
        original_tick_transmit = MeshtasticTransport._tick_transmit
        
        def logged_send_message(self, envelope: MessageEnvelope, destination: str, chunk_delay: float = 0.0):
            """Wrapped send_message that logs chunks (direct send path, when spool disabled)."""
            if _message_logger:
                _message_logger.log_sent(destination, envelope)
                # Log chunking details
                chunks = list(chunk_envelope(envelope, self.segment_size))
                chunk_sizes = [len(chunk) for chunk in chunks]
                _message_logger.log_message_chunked(envelope.id, len(chunks), chunk_sizes, destination)
                # Log each chunk as it's sent (chunks are logged by radio wrapper, but we can also log here)
                # Actually, the original_send will call radio.send which is wrapped, so chunks will be logged there
            result = original_send(self, envelope, destination, chunk_delay)
            # Only log completion if spool is disabled (direct send path)
            # When spool is enabled, send_message just calls enqueue() and doesn't actually send,
            # so completion will be logged by logged_tick_transmit instead
            if _message_logger and not (self._enable_spool and self.spool is not None):
                chunks = list(chunk_envelope(envelope, self.segment_size))
                _message_logger.log_message_complete(envelope.id, len(chunks), "sent", destination)
            return result
        
        def logged_receive_message(self, timeout: float = 0.5):
            """Wrapped receive_message that logs chunks and complete messages."""
            # Track chunks received for this call
            chunks_received_count = {}
            
            # We need to intercept chunk receives, so we'll wrap the radio receive
            # But chunks are already logged by the radio wrapper, so we just need to
            # track completion here
            result = original_receive(self, timeout)
            if _message_logger and result[0] is not None and result[1] is not None:
                sender, envelope = result
                _message_logger.log_received(sender, envelope)
                # Try to get chunk count from reassembler if available
                # The reassembler tracks chunks per message ID
                if hasattr(self.reassembler, '_buckets'):
                    for msg_id, bucket in self.reassembler._buckets.items():
                        if msg_id.startswith(envelope.id[:8]):  # Match by prefix
                            total_chunks = getattr(bucket, 'total', None)
                            if total_chunks:
                                _message_logger.log_message_complete(
                                    envelope.id, total_chunks, "received", sender
                                )
                                break
            return result
        
        def logged_enqueue(self, envelope: MessageEnvelope, destination: str):
            """Wrapped enqueue that logs when messages are queued (spool path)."""
            if _message_logger:
                _message_logger.log_sent(destination, envelope)
                # Log chunking details
                chunks = list(chunk_envelope(envelope, self.segment_size))
                chunk_sizes = [len(chunk) for chunk in chunks]
                _message_logger.log_message_chunked(envelope.id, len(chunks), chunk_sizes, destination)
            return original_enqueue(self, envelope, destination)
        
        def logged_get_chunks(self, msg_id: str, envelope: MessageEnvelope):
            """Wrapped _get_or_create_chunks that logs chunking details."""
            chunks = original_get_chunks(self, msg_id, envelope)
            # Chunking is logged in enqueue/send_message, but we can also log here for completeness
            return chunks
        
        def logged_tick_transmit(self):
            """Wrapped _tick_transmit that logs chunk transmissions."""
            if not self.spool:
                return original_tick_transmit(self)
            
            due = self.spool.due()
            if not due:
                return original_tick_transmit(self)
            
            msg_id, entry = due[0]
            
            try:
                envelope = MessageEnvelope.from_dict(entry.envelope)
            except (KeyError, TypeError):
                return original_tick_transmit(self)
            
            # Get chunks (this will use our logged version)
            chunks = self._get_or_create_chunks(msg_id, envelope)
            next_seq_before = self._get_next_seq(msg_id)
            was_in_progress_before = msg_id in self._active_progress
            destination = entry.destination
            
            # Call original to do the actual transmission
            result = original_tick_transmit(self)
            
            # Check if message completed (all chunks sent)
            # Completion occurs when next_seq advances past len(chunks)
            # The original code clears progress when next_seq > len(chunks), so we check:
            # 1. If next_seq advanced past total chunks: (before <= len) and (after > len)
            # 2. If progress was cleared: was in progress before, not in progress after
            next_seq_after = self._get_next_seq(msg_id)
            is_still_in_progress = msg_id in self._active_progress
            
            if _message_logger:
                # Message completed if next_seq advanced past total chunks
                # OR if we were in progress and now we're not (progress was cleared)
                completed = False
                if next_seq_before <= len(chunks) and next_seq_after > len(chunks):
                    completed = True
                elif was_in_progress_before and not is_still_in_progress:
                    # Progress was cleared, meaning all chunks were sent
                    # This handles cases where completion detection happens in the next tick
                    completed = True
                
                if completed:
                    _message_logger.log_message_complete(msg_id, len(chunks), "sent", destination)
            
            return result
        
        # Also patch the radio interface to log chunk receives
        # We need to wrap the radio's receive method
        original_radio_receive = None
        original_radio_send = None
        
        def wrap_radio(radio_instance):
            """Wrap a radio instance to log chunk receives."""
            if hasattr(radio_instance, '_wrapped_for_logging'):
                return  # Already wrapped
            
            original_send = radio_instance.send
            original_receive = radio_instance.receive
            
            def logged_radio_send(destination: str, payload: bytes):
                """Log radio sends (chunks)."""
                # Extract message ID from chunk header if possible
                try:
                    from atlas_meshtastic_bridge.message import parse_chunk
                    flags, chunk_id, chunk_seq, chunk_total, chunk_payload = parse_chunk(payload)
                    # Only log if not an ACK (ACKs are control messages)
                    if not (flags & 0x01) and _message_logger:
                        _message_logger.log_chunk_sent(
                            chunk_id, chunk_seq, chunk_total, len(payload), destination
                        )
                except (ValueError, IndexError, ImportError):
                    pass  # Not a valid chunk or module unavailable, skip logging
                return original_send(destination, payload)
            
            def logged_radio_receive(timeout: float):
                """Log radio receives (chunks)."""
                result = original_receive(timeout)
                if result and _message_logger:
                    sender, payload = result
                    try:
                        from atlas_meshtastic_bridge.message import parse_chunk
                        flags, chunk_id, chunk_seq, chunk_total, chunk_payload = parse_chunk(payload)
                        if not (flags & 0x01):  # Not an ACK
                            _message_logger.log_chunk_received(
                                chunk_id, chunk_seq, chunk_total, len(payload), sender
                            )
                    except (ValueError, IndexError, ImportError):
                        pass  # Not a valid chunk or module unavailable, skip logging
                return result
            
            radio_instance.send = logged_radio_send
            radio_instance.receive = logged_radio_receive
            radio_instance._wrapped_for_logging = True
        
        # Patch transport methods
        MeshtasticTransport.send_message = logged_send_message
        MeshtasticTransport.receive_message = logged_receive_message
        MeshtasticTransport.enqueue = logged_enqueue
        MeshtasticTransport._get_or_create_chunks = logged_get_chunks
        MeshtasticTransport._tick_transmit = logged_tick_transmit
        
        # Patch the transport's __init__ to wrap the radio
        original_init = MeshtasticTransport.__init__
        
        def logged_init(self, radio, *args, **kwargs):
            """Wrapped __init__ that wraps the radio for logging."""
            original_init(self, radio, *args, **kwargs)
            wrap_radio(self.radio)
        
        MeshtasticTransport.__init__ = logged_init
        
        logging.info("Message and chunk-level logging enabled - transmissions will be logged to file")
    except Exception as e:
        logging.warning("Failed to patch transport for message logging: %s", e)

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
    global _message_logger
    
    config = load_config()

    # Configure logging early
    log_level = str(config.get("log_level", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.info("Loaded config from %s: %s", CURRENT_DIR / "config.json", {k: v for k, v in config.items() if k != "api_token"})
    
    # Initialize message logger if enabled
    enable_logging = config.get("enable_message_logging", False)
    if enable_logging:
        message_log_path = CURRENT_DIR / "message_log.txt"
        _message_logger = MessageLogger(message_log_path)
        logging.info("Message logging enabled - log file: %s", message_log_path)
        # Patch transport for message logging (must happen before bridge_main creates transport)
        _patch_transport_for_logging()
    else:
        logging.info("Message logging disabled")

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
