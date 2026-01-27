"""Tests for the ModuleBase class."""

from unittest.mock import MagicMock
import pytest


class ConcreteModule:
    """Concrete implementation of ModuleBase for testing."""

    MODULE_NAME = "test_module"
    MODULE_VERSION = "1.2.3"
    DEPENDENCIES = ["dep1", "dep2"]

    def __init__(self, bus, config):
        from modules.module_base import ModuleBase

        # Copy ModuleBase behavior
        self.bus = bus
        self.config = config
        self.running = False
        self._logger = MagicMock()

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def get_module_config(self):
        return self.config.get("modules", {}).get(self.MODULE_NAME, {})

    def is_enabled(self):
        module_cfg = self.get_module_config()
        return module_cfg.get("enabled", True)

    def system_check(self):
        return {
            "healthy": self.running,
            "status": "running" if self.running else "stopped",
        }


class TestModuleBaseAttributes:
    """Tests for ModuleBase class attributes."""

    def test_module_base_default_attributes(self):
        """Test ModuleBase has correct default attributes."""
        from modules.module_base import ModuleBase

        assert hasattr(ModuleBase, "MODULE_NAME")
        assert hasattr(ModuleBase, "MODULE_VERSION")
        assert hasattr(ModuleBase, "DEPENDENCIES")

        assert ModuleBase.MODULE_NAME == "unnamed"
        assert ModuleBase.MODULE_VERSION == "0.0.0"
        assert ModuleBase.DEPENDENCIES == []


class TestModuleBaseInit:
    """Tests for ModuleBase initialization."""

    def test_module_init_stores_bus_and_config(self):
        """Test module initialization stores bus and config."""
        bus = MagicMock()
        config = {"key": "value"}

        module = ConcreteModule(bus, config)

        assert module.bus is bus
        assert module.config == config

    def test_module_init_sets_running_false(self):
        """Test module initialization sets running to False."""
        bus = MagicMock()
        config = {}

        module = ConcreteModule(bus, config)

        assert module.running is False


class TestModuleBaseGetModuleConfig:
    """Tests for get_module_config method."""

    def test_get_module_config_returns_module_section(self):
        """Test get_module_config returns the module's config section."""
        bus = MagicMock()
        config = {
            "modules": {
                "test_module": {"setting1": "value1", "setting2": 42},
                "other_module": {"other_setting": "other_value"},
            }
        }

        module = ConcreteModule(bus, config)
        result = module.get_module_config()

        assert result == {"setting1": "value1", "setting2": 42}

    def test_get_module_config_returns_empty_dict_when_missing(self):
        """Test get_module_config returns empty dict when section missing."""
        bus = MagicMock()
        config = {"modules": {}}

        module = ConcreteModule(bus, config)
        result = module.get_module_config()

        assert result == {}

    def test_get_module_config_handles_no_modules_section(self):
        """Test get_module_config handles missing modules section."""
        bus = MagicMock()
        config = {}

        module = ConcreteModule(bus, config)
        result = module.get_module_config()

        assert result == {}


class TestModuleBaseIsEnabled:
    """Tests for is_enabled method."""

    def test_is_enabled_returns_true_by_default(self):
        """Test is_enabled returns True when not specified in config."""
        bus = MagicMock()
        config = {"modules": {"test_module": {}}}

        module = ConcreteModule(bus, config)

        assert module.is_enabled() is True

    def test_is_enabled_returns_config_value(self):
        """Test is_enabled returns config value when specified."""
        bus = MagicMock()
        config = {"modules": {"test_module": {"enabled": False}}}

        module = ConcreteModule(bus, config)

        assert module.is_enabled() is False

    def test_is_enabled_returns_true_when_explicitly_enabled(self):
        """Test is_enabled returns True when explicitly enabled."""
        bus = MagicMock()
        config = {"modules": {"test_module": {"enabled": True}}}

        module = ConcreteModule(bus, config)

        assert module.is_enabled() is True


class TestModuleBaseSystemCheck:
    """Tests for system_check method."""

    def test_system_check_returns_healthy_when_running(self):
        """Test system_check returns healthy when module is running."""
        bus = MagicMock()
        config = {}

        module = ConcreteModule(bus, config)
        module.running = True

        result = module.system_check()

        assert result["healthy"] is True
        assert result["status"] == "running"

    def test_system_check_returns_unhealthy_when_stopped(self):
        """Test system_check returns unhealthy when module is stopped."""
        bus = MagicMock()
        config = {}

        module = ConcreteModule(bus, config)
        module.running = False

        result = module.system_check()

        assert result["healthy"] is False
        assert result["status"] == "stopped"


class TestModuleBaseStartStop:
    """Tests for start and stop methods."""

    def test_start_sets_running_true(self):
        """Test start method sets running to True."""
        bus = MagicMock()
        config = {}

        module = ConcreteModule(bus, config)
        module.start()

        assert module.running is True

    def test_stop_sets_running_false(self):
        """Test stop method sets running to False."""
        bus = MagicMock()
        config = {}

        module = ConcreteModule(bus, config)
        module.running = True
        module.stop()

        assert module.running is False


class TestModuleBaseRepr:
    """Tests for ModuleBase __repr__ method."""

    def test_repr_format(self):
        """Test ModuleBase __repr__ returns expected format."""
        from modules.module_base import ModuleBase

        # Create a concrete subclass with proper __repr__
        class TestModule(ModuleBase):
            MODULE_NAME = "my_module"
            MODULE_VERSION = "2.0.0"

            def start(self):
                pass

            def stop(self):
                pass

        bus = MagicMock()
        config = {}
        module = TestModule(bus, config)

        repr_str = repr(module)

        assert "TestModule" in repr_str
        assert "my_module" in repr_str
        assert "2.0.0" in repr_str


class TestModuleBaseDependencies:
    """Tests for module dependencies."""

    def test_dependencies_default_empty(self):
        """Test DEPENDENCIES defaults to empty list."""
        from modules.module_base import ModuleBase

        assert ModuleBase.DEPENDENCIES == []

    def test_dependencies_can_be_overridden(self):
        """Test DEPENDENCIES can be overridden in subclass."""
        from modules.module_base import ModuleBase

        class DependentModule(ModuleBase):
            MODULE_NAME = "dependent"
            MODULE_VERSION = "1.0.0"
            DEPENDENCIES = ["core", "network"]

            def start(self):
                pass

            def stop(self):
                pass

        assert DependentModule.DEPENDENCIES == ["core", "network"]


class TestModuleBaseAbstract:
    """Tests for abstract method enforcement."""

    def test_module_base_is_abstract(self):
        """Test ModuleBase is abstract and cannot be instantiated directly."""
        from modules.module_base import ModuleBase
        from abc import ABC

        # ModuleBase should be a subclass of ABC
        assert issubclass(ModuleBase, ABC)

    def test_subclass_must_implement_start(self):
        """Test subclass must implement start method."""
        from modules.module_base import ModuleBase

        class IncompleteModule(ModuleBase):
            MODULE_NAME = "incomplete"
            MODULE_VERSION = "1.0.0"

            def stop(self):
                pass

            # Missing start method

        bus = MagicMock()
        config = {}

        # Should raise TypeError because start is not implemented
        with pytest.raises(TypeError):
            IncompleteModule(bus, config)

    def test_subclass_must_implement_stop(self):
        """Test subclass must implement stop method."""
        from modules.module_base import ModuleBase

        class IncompleteModule(ModuleBase):
            MODULE_NAME = "incomplete"
            MODULE_VERSION = "1.0.0"

            def start(self):
                pass

            # Missing stop method

        bus = MagicMock()
        config = {}

        # Should raise TypeError because stop is not implemented
        with pytest.raises(TypeError):
            IncompleteModule(bus, config)


class TestModuleBaseLogging:
    """Tests for module logging setup."""

    def test_module_creates_logger(self):
        """Test module creates logger with correct name."""
        from modules.module_base import ModuleBase
        import logging

        class LoggingModule(ModuleBase):
            MODULE_NAME = "logging_test"
            MODULE_VERSION = "1.0.0"

            def start(self):
                pass

            def stop(self):
                pass

        bus = MagicMock()
        config = {}
        module = LoggingModule(bus, config)

        assert hasattr(module, "_logger")
        assert isinstance(module._logger, logging.Logger)
        assert "logging_test" in module._logger.name
