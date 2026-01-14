"""Module loader for BasePlate OS.

Discovers, validates, and loads modules from the modules/ directory
with automatic dependency ordering.
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from modules.module_base import ModuleBase

LOGGER = logging.getLogger("module_loader")


class ModuleLoadError(Exception):
    """Raised when a module fails to load."""
    pass


class DependencyError(Exception):
    """Raised when module dependencies cannot be resolved."""
    pass


class ModuleLoader:
    """
    Discovers and loads modules from the modules/ directory.
    
    Handles:
        - Auto-discovery of modules
        - Dependency resolution and ordering
        - Module instantiation and lifecycle management
    """
    
    def __init__(self, bus, config: Dict[str, Any], modules_dirs: list[Path] | None = None):
        self.bus = bus
        self.config = config
        if modules_dirs is None:
            # Default: search ATLAS_ASSET_OS/modules/ first, then modules/ relative to config
            asset_os_modules = Path(__file__).resolve().parent
            config_dir = Path(config.get("_config_dir", Path.cwd()))
            user_modules = config_dir / "modules"
            modules_dirs = [asset_os_modules, user_modules]
        self.modules_dirs = [Path(d) for d in modules_dirs]
        self._module_classes: Dict[str, Type[ModuleBase]] = {}
        self._module_instances: Dict[str, ModuleBase] = {}
        self._load_order: List[str] = []
    
    def discover_modules(self) -> Dict[str, Type[ModuleBase]]:
        """
        Discover all valid modules from multiple module directories.
        
        Searches directories in order, with later directories overriding earlier ones
        if they contain modules with the same MODULE_NAME.
        
        A valid module has:
            - A manager.py file
            - A class that inherits from ModuleBase with MODULE_NAME defined
            
        Returns:
            Dict mapping module names to their manager classes
        """
        discovered: Dict[str, Type[ModuleBase]] = {}
        
        for modules_dir in self.modules_dirs:
            if not modules_dir.exists():
                LOGGER.debug("Modules directory not found: %s (skipping)", modules_dir)
                continue
            
            LOGGER.debug("Searching for modules in: %s", modules_dir)
            
            for item in modules_dir.iterdir():
                if not item.is_dir():
                    continue
                if item.name.startswith("_"):
                    continue
                
                manager_path = item / "manager.py"
                if not manager_path.exists():
                    LOGGER.debug("Skipping %s: no manager.py", item.name)
                    continue
                
                try:
                    # Import the module's manager
                    module_name = f"modules.{item.name}.manager"
                    spec = importlib.util.spec_from_file_location(module_name, manager_path)
                    if spec is None or spec.loader is None:
                        LOGGER.warning("Could not load spec for %s", item.name)
                        continue
                    
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find the ModuleBase subclass
                    manager_class = None
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, ModuleBase) and 
                            attr is not ModuleBase):
                            manager_class = attr
                            break
                    
                    if manager_class is None:
                        LOGGER.debug("Skipping %s: no ModuleBase subclass found", item.name)
                        continue
                    
                    # Validate MODULE_NAME is set
                    if manager_class.MODULE_NAME == "unnamed":
                        LOGGER.warning("Module %s has unnamed MODULE_NAME, using directory name", item.name)
                        manager_class.MODULE_NAME = item.name
                    
                    # Later directories override earlier ones
                    if manager_class.MODULE_NAME in discovered:
                        LOGGER.debug("Overriding module %s from %s with version from %s", 
                                   manager_class.MODULE_NAME, discovered[manager_class.MODULE_NAME], modules_dir)
                    
                    discovered[manager_class.MODULE_NAME] = manager_class
                    LOGGER.info(
                        "Discovered module: %s v%s (from %s)",
                        manager_class.MODULE_NAME,
                        manager_class.MODULE_VERSION,
                        modules_dir.name,
                    )
                    
                except Exception as e:
                    LOGGER.error("Error discovering module %s: %s", item.name, e)
                    continue
        
        self._module_classes = discovered
        return discovered
    
    def resolve_dependencies(self) -> List[str]:
        """
        Resolve module dependencies and determine load order.
        
        Uses topological sort to ensure dependencies are loaded first.
        
        Returns:
            List of module names in load order
            
        Raises:
            DependencyError: If circular dependencies or missing dependencies detected
        """
        modules_cfg = self.config.get("modules", {})
        
        # Filter to only enabled modules
        enabled_modules = {}
        for name, cls in self._module_classes.items():
            module_cfg = modules_cfg.get(name, {})
            if module_cfg.get("enabled", True):
                enabled_modules[name] = cls
            else:
                LOGGER.info("Module %s is disabled in config", name)
        
        # Check for missing dependencies
        for name, cls in enabled_modules.items():
            for dep in cls.DEPENDENCIES:
                if dep not in enabled_modules:
                    if dep in self._module_classes:
                        raise DependencyError(
                            f"Module '{name}' depends on '{dep}' which is disabled"
                        )
                    else:
                        raise DependencyError(
                            f"Module '{name}' depends on '{dep}' which is not found"
                        )
        
        # Topological sort using Kahn's algorithm
        in_degree = {name: 0 for name in enabled_modules}
        for name, cls in enabled_modules.items():
            for dep in cls.DEPENDENCIES:
                if dep in in_degree:
                    in_degree[name] += 1
        
        # Start with modules that have no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        load_order = []
        
        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            current = queue.pop(0)
            load_order.append(current)
            
            # Reduce in-degree for modules that depend on current
            for name, cls in enabled_modules.items():
                if current in cls.DEPENDENCIES:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)
        
        # Check for circular dependencies
        if len(load_order) != len(enabled_modules):
            remaining = set(enabled_modules.keys()) - set(load_order)
            raise DependencyError(
                f"Circular dependency detected among: {remaining}"
            )
        
        self._load_order = load_order
        LOGGER.info("Module load order: %s", " -> ".join(load_order))
        return load_order
    
    def load_modules(self) -> List[ModuleBase]:
        """
        Instantiate all enabled modules in dependency order.
        
        Returns:
            List of module instances in load order
        """
        instances = []
        
        for name in self._load_order:
            cls = self._module_classes[name]
            try:
                instance = cls(self.bus, self.config)
                self._module_instances[name] = instance
                instances.append(instance)
                LOGGER.info("Loaded module: %s", instance)
            except Exception as e:
                LOGGER.error("Failed to instantiate module %s: %s", name, e)
                raise ModuleLoadError(f"Failed to load module {name}: {e}")
        
        return instances
    
    def start_modules(self) -> None:
        """Start all loaded modules in dependency order."""
        for name in self._load_order:
            instance = self._module_instances.get(name)
            if instance:
                try:
                    LOGGER.info("Starting module: %s", name)
                    instance.start()
                except Exception as e:
                    LOGGER.error("Failed to start module %s: %s", name, e)
                    raise ModuleLoadError(f"Failed to start module {name}: {e}")
    
    def stop_modules(self) -> None:
        """Stop all loaded modules in reverse dependency order."""
        for name in reversed(self._load_order):
            instance = self._module_instances.get(name)
            if instance:
                try:
                    LOGGER.info("Stopping module: %s", name)
                    instance.stop()
                except Exception as e:
                    LOGGER.error("Error stopping module %s: %s", name, e)
    
    def get_module(self, name: str) -> Optional[ModuleBase]:
        """Get a loaded module instance by name."""
        return self._module_instances.get(name)
    
    def list_modules(self) -> List[str]:
        """List all loaded module names."""
        return list(self._load_order)
