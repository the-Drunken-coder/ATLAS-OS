import signal
import sys
import time
import json
import logging
from pathlib import Path
import threading

# Ensure bridge source is on path
_ROOT = Path(__file__).resolve().parents[3]  # ATLAS root
_BRIDGE_SRC = _ROOT / "Atlas_Command" / "connection_packages" / "atlas_meshtastic_bridge" / "src"
_HTTP_CLIENT_SRC = _ROOT / "Atlas_Command" / "connection_packages" / "atlas_asset_http_client_python" / "src"
for p in (str(_BRIDGE_SRC), str(_HTTP_CLIENT_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from bus import MessageBus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
LOGGER = logging.getLogger("master")

class OSManager:
    def __init__(self):
        self.running = True
        self.bus = MessageBus()
        self.config = self._load_config()
        self.modules = []

    def _load_config(self) -> dict:
        config_path = Path(__file__).resolve().parent / "config.json"
        if not config_path.exists():
            LOGGER.error("config.json not found at %s!", config_path)
            sys.exit(1)
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            LOGGER.error(f"Failed to load config: {e}")
            sys.exit(1)

    def _start_modules(self):
        # Import modules dynamically or statically
        # For this version, we'll import them statically to ensure they exist
        try:
            from modules.operations.manager import OperationsManager
            from modules.comms.manager import CommsManager
            
            # Initialize Operations
            if self.config.get("modules", {}).get("operations", {}).get("enabled", True):
                ops_mgr = OperationsManager(self.bus, self.config)
                self.modules.append(ops_mgr)

            # Initialize Comms
            if self.config.get("modules", {}).get("comms", {}).get("enabled", True):
                comms_mgr = CommsManager(self.bus, self.config)
                self.modules.append(comms_mgr)

            # Start all modules
            for mod in self.modules:
                if hasattr(mod, "start"):
                    mod.start()

        except ImportError as e:
            LOGGER.error(f"Failed to import modules: {e}")
        except Exception as e:
            LOGGER.error(f"Failed to start modules: {e}")

    def run(self):
        LOGGER.info("BasePlate OS booting...")
        
        self._start_modules()
        
        self.bus.publish("os.boot_complete", {"ts": time.time()})
        LOGGER.info("Boot sequence complete. Entering main loop.")

        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self, signum=None, frame=None):
        LOGGER.info("Shutdown signal received")
        self.running = False
        self.bus.publish("os.shutdown", {})
        
        # Stop modules
        for mod in self.modules:
            if hasattr(mod, "stop"):
                try:
                    mod.stop()
                except Exception as e:
                    LOGGER.error(f"Error stopping module: {e}")

        self.bus.shutdown()
        LOGGER.info("OS Halted.")
        sys.exit(0)

if __name__ == "__main__":
    os_mgr = OSManager()
    
    # helper for clean shutdown on sigint
    signal.signal(signal.SIGINT, os_mgr.shutdown)
    signal.signal(signal.SIGTERM, os_mgr.shutdown)

    os_mgr.run()
