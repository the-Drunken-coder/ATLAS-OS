# ATLAS Asset Operating Systems

This directory contains the BasePlate OS framework, module library, and example implementations for building asset operating systems that integrate with Atlas Command.

## Structure

```
ATLAS_ASSET_OS/
├── framework/              # Core BasePlate OS framework
│   ├── bus.py             # Message bus for inter-module communication
│   ├── master.py          # Core OS manager
│   └── __init__.py        # Framework exports
│
├── modules/                # Module infrastructure and actual modules
│   ├── module_base.py     # Base class for all modules
│   ├── module_loader.py   # Module discovery and lifecycle management
│   ├── __init__.py        # Module infrastructure exports
│   ├── comms/             # Communications module (Meshtastic bridge)
│   │   ├── manager.py     # CommsManager implementation
│   │   └── functions/     # 34 API function wrappers
│   └── operations/         # Operations module
│       ├── manager.py     # OperationsManager implementation
│       └── registration.py # Asset self-registration helper
│
├── tests/                  # Dedicated testing directory
│   ├── unit/              # Unit tests
│   │   └── test_bus.py    # MessageBus tests
│   ├── integration/       # Integration tests
│   └── conftest.py        # Shared pytest configuration
│
└── testing_tools/          # Testing utilities and harnesses
    └── baseplate_os_testing_suite/
        └── comms_module/
            └── comms_injector.py
```

## Framework (`framework/`)

The core BasePlate OS framework provides:

- **MessageBus**: Thread-safe pub/sub message bus for inter-module communication
- **OSManager**: Core OS manager handling boot, shutdown, and module coordination

## Module Infrastructure (`modules/`)

The module infrastructure provides:

- **ModuleBase**: Abstract base class defining the module interface
- **ModuleLoader**: Automatic module discovery, dependency resolution, and lifecycle management

### Using the Framework

```python
from framework import OSManager, MessageBus
from modules import ModuleBase, ModuleLoader

# Create your OS manager
os_mgr = OSManager(config_path=Path("config.json"))
os_mgr.run()
```

## Modules (`modules/`)

The modules directory contains both the module infrastructure and the actual modules:

**Module Infrastructure:**
- `module_base.py` - Base class for all modules
- `module_loader.py` - Module discovery and lifecycle management

**Actual Modules:**
- **comms**: Meshtastic radio bridge for Atlas Command communication
- **operations**: Message routing, heartbeat, and asset registration

These modules are automatically discovered and available to all OS implementations. You can also create your own modules in a `modules/` directory relative to your config file, which will override shared modules with the same name.

### Creating a Module

```python
from modules.module_base import ModuleBase

class MyModule(ModuleBase):
    MODULE_NAME = "my_module"
    MODULE_VERSION = "1.0.0"
    DEPENDENCIES = ["comms"]  # Optional
    
    def start(self) -> None:
        self.running = True
        # Your startup logic
    
    def stop(self) -> None:
        self.running = False
        # Your shutdown logic
```

Place your module in `modules/my_module/manager.py` (relative to your config file) and it will be automatically discovered. User modules override framework modules with the same name.

## Creating Your Own OS Implementation

To create a new OS implementation:

1. Create a directory for your OS (e.g., `MyAsset_OS/`)
2. Create a `master.py` that uses the framework:

```python
from framework.master import OSManager
from pathlib import Path

class MyAssetOS(OSManager):
    def _get_modules_dirs(self) -> list[Path]:
        # Add custom module directories (ATLAS_ASSET_OS/modules/ is searched automatically)
        custom_modules = Path(__file__).resolve().parent / "modules"
        return [custom_modules]  # Shared modules are added automatically
    
    def run(self):
        # Add any custom boot logic here
        super().run()

if __name__ == "__main__":
    os_mgr = MyAssetOS(config_path=Path("config.json"))
    os_mgr.run()
```

3. Create a `config.json` with your asset configuration
4. Place any custom modules in `modules/` or create a local `modules/` directory

## Testing

Tests are organized in the `tests/` directory:

- **Unit tests** (`tests/unit/`): Test individual components in isolation
- **Integration tests** (`tests/integration/`): Test component interactions

From `ATLAS_ASSET_OS/`, install test dependencies first (installs the Meshtastic bridge and its requirements):
```bash
pip install -r requirements-test.txt
```

Run tests:
```bash
pytest tests/
```

## Configuration

Modules are configured via `config.json`:

```json
{
  "atlas": {
    "base_url": "http://localhost:8000",
    "asset": {
      "id": "asset-001",
      "name": "My Asset",
      "model_id": "generic-asset"
    }
  },
  "modules": {
    "comms": {
      "enabled": true,
      "simulated": false,
      "gateway_node_id": "!9e9f370c"
    },
    "operations": {
      "enabled": true
    }
  }
}
```

## Module Dependencies

Modules can declare dependencies on other modules. The framework automatically resolves dependencies and starts modules in the correct order:

- `comms` has no dependencies (starts first)
- `operations` depends on `comms` (starts after comms)

## Architecture

BasePlate OS uses a modular architecture:

1. **Framework** provides the core OS infrastructure
2. **Modules** provide reusable functionality
3. **Implementations** combine framework + modules + custom logic

This separation allows:
- Framework to evolve independently
- Modules to be shared across implementations
- New OS implementations to be created easily
