"""BasePlate OS Master - Core OS manager for asset operating systems."""

import sys
import threading
import time
import json
import logging
from pathlib import Path

from framework.bus import MessageBus
from framework.utils import is_test_env
from modules.module_loader import ModuleLoader, ModuleLoadError, DependencyError

LOGGER = logging.getLogger("framework.master")


class OSManager:
    """
    Core OS manager for BasePlate OS implementations.

    Handles:
        - Configuration loading
        - Module discovery and lifecycle
        - Signal handling for graceful shutdown
    """

    def __init__(self, config_path: Path | None = None, config: dict | None = None):
        """
        Initialize the OS manager.

        Args:
            config_path: Optional path to config.json. If None, looks for config.json
                        in the same directory as the calling script.
            config: Optional config dict. If provided, takes precedence over config_path.
        """
        self.running = True
        self.bus = MessageBus()

        if config is not None:
            # Use provided config dict directly
            self.config = config.copy()
            self.config.setdefault("_config_dir", Path.cwd())
        else:
            self.config = self._load_config(config_path)

        self.module_loader = ModuleLoader(
            self.bus, self.config, self._get_modules_dirs()
        )

    def _get_modules_dirs(self) -> list[Path]:
        """
        Get the module directories to search.

        By default, searches:
        1. ATLAS_ASSET_OS/modules/ (shared modules)
        2. modules/ relative to config file (user modules)

        Subclasses can override to customize module discovery.
        """
        # Find ATLAS_ASSET_OS/modules directory (where module_loader.py lives)
        import modules.module_loader

        shared_modules_dir = Path(modules.module_loader.__file__).resolve().parent

        # User modules relative to config
        config_dir = Path(self.config.get("_config_dir", Path.cwd()))
        user_modules_dir = config_dir / "modules"

        return [shared_modules_dir, user_modules_dir]

    def _load_config(self, config_path: Path | None = None) -> dict:
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to config.json. If None, searches for config.json
                        in the same directory as the calling script.

        Returns:
            Configuration dictionary with _config_dir added
        """
        if config_path is None:
            # Try to find config.json relative to caller
            import inspect

            frame = inspect.currentframe()
            # Default to current working directory
            caller_dir = Path.cwd()
            # Try to get caller's directory from frame
            if frame and frame.f_back and frame.f_back.f_back:
                back_globals = frame.f_back.f_back.f_globals
                caller_file_str = back_globals.get("__file__")
                if caller_file_str:
                    caller_dir = Path(caller_file_str).parent
            config_path = caller_dir / "config.json"

        if not config_path.exists():
            LOGGER.error("config.json not found at %s!", config_path)
            sys.exit(1)

        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            config["_config_dir"] = config_path.parent
            return config
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

            LOGGER.info(
                "Discovered %d module(s): %s",
                len(discovered),
                ", ".join(discovered.keys()),
            )

            # Resolve dependencies and determine load order
            # Note: Return value not needed here as load order is stored internally
            # and used by subsequent load_modules() and start_modules() calls
            self.module_loader.resolve_dependencies()

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
        """Run the OS main loop."""
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
        """Shutdown the OS gracefully."""
        LOGGER.info("Shutdown signal received")
        self.running = False
        self.bus.publish("os.shutdown", {})

        # Stop modules in reverse dependency order
        self.module_loader.stop_modules()

        self.bus.shutdown()
        LOGGER.info("OS Halted.")
        # Only call sys.exit if we're in the main thread AND not running under pytest
        # This prevents "Exception ignored in thread" warnings during test cleanup
        if not is_test_env() and threading.current_thread() is threading.main_thread():
            sys.exit(0)
