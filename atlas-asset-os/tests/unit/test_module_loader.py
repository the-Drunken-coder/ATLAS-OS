"""Unit tests for module loader functionality."""

import sys
from pathlib import Path

import pytest

# Paths should be set up by conftest.py, but ensure we have them here too
_TEST_DIR = Path(__file__).resolve().parent
_ASSET_OS_ROOT = _TEST_DIR.parents[2]

# Add ATLAS_ASSET_OS root to path so we can import framework and modules
_ASSET_OS_ROOT_STR = str(_ASSET_OS_ROOT.resolve())
if _ASSET_OS_ROOT_STR not in sys.path:
    sys.path.insert(0, _ASSET_OS_ROOT_STR)

from framework.bus import MessageBus  # noqa: E402
from modules.module_loader import ModuleLoader, DependencyError  # noqa: E402


class TestModuleLoader:
    """Unit tests for ModuleLoader."""
    
    @pytest.fixture
    def bus(self):
        """Create a message bus."""
        return MessageBus()
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return {
            "atlas": {
                "base_url": "http://localhost:8000",
                "asset": {
                    "id": "test-asset-001",
                    "name": "Test Asset",
                    "model_id": "test-asset"
                }
            },
            "modules": {
                "comms": {
                    "enabled": True,
                    "simulated": True,
                    "gateway_node_id": "!test123"
                },
                "operations": {
                    "enabled": True
                }
            },
            "_config_dir": str(_ASSET_OS_ROOT)
        }
    
    @pytest.fixture
    def module_loader(self, bus, config):
        """Create a module loader."""
        return ModuleLoader(bus, config)
    
    def test_modules_discovered(self, module_loader):
        """Test that modules are discovered from modules directory."""
        discovered = module_loader.discover_modules()
        assert len(discovered) > 0
        assert "comms" in discovered
        assert "operations" in discovered
    
    def test_dependencies_resolved(self, module_loader):
        """Test that module dependencies are resolved correctly."""
        module_loader.discover_modules()
        load_order = module_loader.resolve_dependencies()
        
        # comms should come before operations (operations depends on comms)
        assert "comms" in load_order
        assert "operations" in load_order
        assert load_order.index("comms") < load_order.index("operations")
    
    def test_modules_load(self, module_loader):
        """Test that modules can be loaded."""
        module_loader.discover_modules()
        module_loader.resolve_dependencies()
        instances = module_loader.load_modules()
        
        assert len(instances) > 0
        assert any(m.MODULE_NAME == "comms" for m in instances)
        assert any(m.MODULE_NAME == "operations" for m in instances)
    
    def test_modules_start(self, module_loader):
        """Test that modules can be started."""
        module_loader.discover_modules()
        module_loader.resolve_dependencies()
        module_loader.load_modules()
        module_loader.start_modules()
        
        # Verify modules are running
        comms_module = module_loader.get_module("comms")
        operations_module = module_loader.get_module("operations")
        
        assert comms_module is not None
        assert operations_module is not None
        assert comms_module.running is True
        assert operations_module.running is True
    
    def test_modules_stop(self, module_loader):
        """Test that modules can be stopped gracefully."""
        module_loader.discover_modules()
        module_loader.resolve_dependencies()
        module_loader.load_modules()
        module_loader.start_modules()
        
        # Stop modules
        module_loader.stop_modules()
        
        # Verify modules are stopped
        comms_module = module_loader.get_module("comms")
        operations_module = module_loader.get_module("operations")
        
        assert comms_module.running is False
        assert operations_module.running is False
    
    def test_disabled_module_not_loaded(self, bus, config):
        """Test that disabled modules are not loaded."""
        config["modules"]["comms"]["enabled"] = False
        loader = ModuleLoader(bus, config)
        loader.discover_modules()
        
        # operations should fail because it depends on disabled comms
        with pytest.raises(DependencyError, match="depends on 'comms' which is disabled"):
            loader.resolve_dependencies()
    
    def test_get_module(self, module_loader):
        """Test getting a module by name."""
        module_loader.discover_modules()
        module_loader.resolve_dependencies()
        module_loader.load_modules()
        
        comms = module_loader.get_module("comms")
        assert comms is not None
        assert comms.MODULE_NAME == "comms"
        
        nonexistent = module_loader.get_module("nonexistent")
        assert nonexistent is None
    
    def test_list_modules(self, module_loader):
        """Test listing loaded modules."""
        module_loader.discover_modules()
        module_loader.resolve_dependencies()
        module_loader.load_modules()
        
        modules = module_loader.list_modules()
        assert len(modules) > 0
        assert "comms" in modules
        assert "operations" in modules
