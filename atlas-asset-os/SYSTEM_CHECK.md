# System Check for ATLAS Asset OS

## Overview

ATLAS Asset OS supports module health diagnostics through a shared `system_check()` contract.
Checks can be run directly through `ModuleLoader` or via bus request/response.

## How It Works

### Module Base Contract

- **File**: `Atlas_Client_Systems/ATLAS_ASSET_OS/modules/module_base.py`
- Every module inherits `system_check()`.
- Default result is:
  - `healthy = self.running`
  - `status = "running"` or `"stopped"`

### Aggregation in Module Loader

- **File**: `Atlas_Client_Systems/ATLAS_ASSET_OS/modules/module_loader.py`
- `run_system_check(timeout_s=5.0)`:
  - runs checks for loaded modules
  - executes each check in a thread with timeout
  - marks timeout or invalid response as unhealthy
  - returns `overall_healthy` and per-module diagnostics

### Bus Flow

- **File**: `Atlas_Client_Systems/ATLAS_ASSET_OS/modules/operations/manager.py`
  - subscribes to `system.check.request`
  - forwards request to `module_loader.system_check.request`
- **File**: `Atlas_Client_Systems/ATLAS_ASSET_OS/framework/master.py`
  - subscribes to `module_loader.system_check.request`
  - publishes results on `system.check.response`

## Module-Specific Diagnostics

### `comms`

- `healthy`, `status`
- active `method`
- `simulated`
- `queued_requests`

### `operations`

- `healthy`, `status`
- `heartbeat_interval_s`
- effective `checkin_interval_s`
- `registration_complete`
- `active_command`
- `queued_commands`

### `sensors`

- `healthy`, `status`
- per-worker health map in `workers`
- `worker_count`

### `data_store`

- `healthy`, `status`
- `namespaces`
- `total_records`
- `persistence_enabled`

## Usage

### Trigger a Check

```python
# Via bus
bus.publish("system.check.request", {"request_id": "unique-id"})

# Directly
results = os_manager.module_loader.run_system_check(timeout_s=5.0)
```

### Aggregated Result Shape

```python
{
    "overall_healthy": bool,
    "modules": {
        "module_name": {
            "healthy": bool,
            "status": str,
            "error": str,  # optional
            # module-specific fields...
        }
    },
}
```

### Bus Response Shape

```python
{
    "results": {
        "overall_healthy": bool,
        "modules": {...}
    },
    "timestamp": float,
    "request_id": str,  # present when provided in request
}
```

## Verification

System check behavior is covered in:
- `Atlas_Client_Systems/ATLAS_ASSET_OS/tests/unit/test_system_check.py`

Run:

```bash
cd Atlas_Client_Systems/ATLAS_ASSET_OS
python -m pytest tests/unit/test_system_check.py -v
python -m pytest tests/ -v
```

## Demo

```bash
cd Atlas_Client_Systems/ATLAS_ASSET_OS
python demo_system_check.py
```
