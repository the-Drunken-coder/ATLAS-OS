"""Base class for BasePlate OS modules.

All modules should inherit from ModuleBase and implement the required interface.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger("module_base")


class ModuleBase(ABC):
    """
    Base class for all BasePlate OS modules.
    
    Modules must define:
        MODULE_NAME: Unique identifier for the module
        MODULE_VERSION: Semantic version string
        
    Modules may define:
        DEPENDENCIES: List of module names this module depends on
        
    Modules must implement:
        start(): Called when module should begin operation
        stop(): Called when module should cease operation
    """
    
    MODULE_NAME: str = "unnamed"
    MODULE_VERSION: str = "0.0.0"
    DEPENDENCIES: List[str] = []
    
    def __init__(self, bus, config: Dict[str, Any]):
        """
        Initialize the module.
        
        Args:
            bus: MessageBus instance for inter-module communication
            config: Full configuration dictionary
        """
        self.bus = bus
        self.config = config
        self.running = False
        self._logger = logging.getLogger(f"modules.{self.MODULE_NAME}")
    
    @abstractmethod
    def start(self) -> None:
        """Start the module. Called after all dependencies have started."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the module. Called before dependencies are stopped."""
        pass
    
    def get_module_config(self) -> Dict[str, Any]:
        """Get this module's configuration section."""
        return self.config.get("modules", {}).get(self.MODULE_NAME, {})
    
    def is_enabled(self) -> bool:
        """Check if this module is enabled in config."""
        module_cfg = self.get_module_config()
        return module_cfg.get("enabled", True)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.MODULE_NAME}@{self.MODULE_VERSION}>"
