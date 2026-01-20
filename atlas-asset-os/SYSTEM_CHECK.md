# System Check Implementation for ATLAS Asset OS

## Overview
This document describes the system check functionality added to the ATLAS Asset OS, which allows modules to report their health status and enables coordinated diagnostics across the entire system.

## Implementation Details

### Core Components

#### 1. ModuleBase Extension
- **File**: `ATLAS_ASSET_OS/modules/module_base.py`
- **Change**: Added `system_check()` method
- **Default Implementation**: Returns `{"healthy": self.running, "status": "running" if self.running else "stopped"}`
- **Purpose**: Provides a consistent interface for all modules to report their health

#### 2. ModuleLoader System Check
- **File**: `ATLAS_ASSET_OS/modules/module_loader.py`
- **Method**: `run_system_check(timeout_s: float = 5.0)`
- **Features**:
  - Runs system check on all loaded modules
  - Executes each check in a separate thread with timeout
  - Treats timeout or no response as unhealthy
  - Returns overall health status and per-module diagnostics
  
#### 3. OSManager Integration
- **File**: `ATLAS_ASSET_OS/framework/master.py`
- **Method**: `_handle_system_check_request(data: Optional[Dict[str, Any]])`
- **Subscription**: Listens to `module_loader.system_check.request`
- **Response**: Publishes to `system.check.response`

#### 4. Operations Manager
- **File**: `ATLAS_ASSET_OS/modules/operations/manager.py`
- **Subscription**: Listens to `system.check.request`
- **Action**: Forwards request to module loader via `module_loader.system_check.request`
- **Custom Diagnostics**: Reports heartbeat interval, checkin status, registration status, command queue

### Module-Specific Implementations

#### Comms Module
Reports:
- Connection status
- Active method (wifi/meshtastic)
- Simulated mode flag
- Queued requests count

#### Operations Module
Reports:
- Heartbeat interval
- Checkin interval
- Registration completion status
- Active command presence
- Queued commands count

#### Sensors Module
Reports:
- Worker health status
- Worker count
- Individual worker types
- Overall health based on all workers

#### Data Store Module
Reports:
- Number of namespaces
- Total record count
- Persistence enabled flag

## Usage

### Triggering a System Check

```python
# Via bus (from any module)
bus.publish("system.check.request", {"request_id": "unique-id"})

# Or directly via module loader
results = os_manager.module_loader.run_system_check(timeout_s=5.0)
```

### Response Format

```python
{
    "overall_healthy": bool,
    "modules": {
        "module_name": {
            "healthy": bool,
            "status": str,
            "error": str (if check failed),
            ...additional module-specific data
        }
    }
}
```

### Bus Response Format

```python
{
    "results": {
        "overall_healthy": bool,
        "modules": {...}
    },
    "timestamp": float,
    "request_id": str (if provided in request)
}
```

## Testing

### Test Coverage
- 8 new comprehensive tests in `ATLAS_ASSET_OS/tests/unit/test_system_check.py`
- All 107 existing tests continue to pass
- Tests cover:
  - Default ModuleBase implementation
  - Module loader system check
  - Bus-based request/response
  - Timeout handling
  - Individual module implementations

### Running Tests

```bash
# Run system check tests
cd ATLAS
python -m pytest ATLAS_ASSET_OS/tests/unit/test_system_check.py -v

# Run all Asset OS tests
python -m pytest ATLAS_ASSET_OS/tests/unit/ -v
```

## Demonstration

A demonstration script is provided at `ATLAS_ASSET_OS/demo_system_check.py`:

```bash
cd ATLAS_ASSET_OS
python demo_system_check.py
```

This script shows:
- Module initialization and startup
- Direct system check invocation
- Bus-based system check request
- Detailed health reporting for all modules

## Key Design Decisions

1. **Timeout Handling**: Each module check runs in a thread with configurable timeout (default 5s)
2. **No Response = Unhealthy**: If a module doesn't respond or times out, it's marked as unhealthy
3. **Optional Override**: Modules can override `system_check()` or use the default implementation
4. **Bus-Based**: Uses the existing message bus pattern for consistency
5. **Non-Blocking**: System checks run in separate threads to avoid blocking operations
6. **Comprehensive Info**: Each module provides custom diagnostics relevant to its function

## Future Enhancements

Potential improvements (not implemented in this PR):
- Periodic automatic system checks
- Historical health tracking
- Alert thresholds and notifications
- Integration with Atlas Command for remote monitoring
- Health check metrics export

## Files Modified

1. `ATLAS_ASSET_OS/modules/module_base.py` - Added system_check method
2. `ATLAS_ASSET_OS/modules/module_loader.py` - Added run_system_check method
3. `ATLAS_ASSET_OS/framework/master.py` - Added system check request handler
4. `ATLAS_ASSET_OS/modules/operations/manager.py` - Added system check implementation and request handling
5. `ATLAS_ASSET_OS/modules/comms/manager.py` - Added system check implementation
6. `ATLAS_ASSET_OS/modules/sensors/manager.py` - Added system check implementation
7. `ATLAS_ASSET_OS/modules/data_store/manager.py` - Added system check implementation

## Files Added

1. `ATLAS_ASSET_OS/tests/unit/test_system_check.py` - Comprehensive tests
2. `ATLAS_ASSET_OS/demo_system_check.py` - Demonstration script
