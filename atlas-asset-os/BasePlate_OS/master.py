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
from module_loader import ModuleLoader, ModuleLoadError, DependencyError

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
        self.module_loader = ModuleLoader(self.bus, self.config)

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
        """Discover, load, and start all enabled modules."""
        try:
            # Discover available modules
            discovered = self.module_loader.discover_modules()
            if not discovered:
                LOGGER.warning("No modules discovered")
                return
            
            LOGGER.info("Discovered %d module(s): %s", len(discovered), ", ".join(discovered.keys()))
            
            # Resolve dependencies and determine load order
            load_order = self.module_loader.resolve_dependencies()
            
            # Load and instantiate modules
            self.module_loader.load_modules()
            
            # Start all modules
            self.module_loader.start_modules()
            
        except DependencyError as e:
            LOGGER.error(f"Module dependency error: {e}")
            sys.exit(1)
        except ModuleLoadError as e:
            LOGGER.error(f"Module load error: {e}")
            sys.exit(1)
        except Exception as e:
            LOGGER.error(f"Failed to start modules: {e}")
            sys.exit(1)

    def run(self):
        LOGGER.info("BasePlate OS booting...")
        
        self._start_modules()
        
        # Register asset with Atlas Command
        try:
            from modules.operations.registration import register_asset
            LOGGER.info("Registering asset with Atlas Command...")
            if register_asset(self.bus, self.config):
                LOGGER.info("Asset registration completed successfully")
            else:
                LOGGER.warning("Asset registration failed, continuing boot sequence")
        except Exception as e:
            LOGGER.error(f"Error during asset registration: {e}")
            LOGGER.warning("Continuing boot sequence despite registration failure")
        
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
        
        # Stop modules in reverse dependency order
        self.module_loader.stop_modules()

        self.bus.shutdown()
        LOGGER.info("OS Halted.")
        sys.exit(0)

if __name__ == "__main__":
    os_mgr = OSManager()
    
    # helper for clean shutdown on sigint
    signal.signal(signal.SIGINT, os_mgr.shutdown)
    signal.signal(signal.SIGTERM, os_mgr.shutdown)

    os_mgr.run()
