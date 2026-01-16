# ATLAS Asset OS Module Catalog

This catalog documents all modules available in the ATLAS Asset OS ecosystem, including production modules and work-in-progress modules.

---

## Production Modules

### `comms` - Communications Manager
**Version:** 1.0.0  
**Purpose:** Multi-transport comms layer (wifi direct + Meshtastic bridge)  

**Capabilities:**
- Transport selection and connection management
- Message sending and receiving (transport dependent)
- Function registry for Atlas Command API calls
- Reliability strategies (retry, acknowledgment)
 - Spooling for offline message handling
 
**Dependencies:** None  
 
**Configuration:**
```json
{
  "comms": {
    "enabled": true,
    "enabled_methods": ["wifi", "meshtastic"],
    "simulated": false,
    "gateway_node_id": "gateway",
    "radio_port": "auto",
    "mode": "general",
    "spool_path": "~/.baseplate_comm_spool.json",
    "wifi": {
      "connect_on_start": true,
      "scan_public_networks": true,
      "networks": [],
      "interface": null,
      "timeout_s": 10.0
    }
  }
}
```

Dev-only priority list (not user config):
- `modules/comms/comms_priority.json` controls the method order (default `wifi`, then `meshtastic`).

---

### `operations` - Operations Manager
**Version:** 1.0.0  
**Purpose:** Message routing, heartbeat, and command handling  

**Capabilities:**
- Route incoming messages to appropriate topics
- Asset self-registration on startup
- Publish periodic heartbeat (default 30s)
- Periodic Atlas Command check-ins (interval depends on comms method)
- Periodic data store snapshot sync on the bus
- Broadcast track telemetry updates when tracks move enough
- Register and execute supported commands from enabled modules
- Command/request/data/error message type classification
 - Forward commands to command handlers

**Bus Topics:**
- Subscribe `commands.register` `{command, handler}`
- Subscribe `commands.unregister` `{command}`
 
**Dependencies:** `comms`  
 
**Configuration:**
```json
{
  "operations": {
    "enabled": true,
    "heartbeat_interval_s": 30.0,
    "checkin_interval_s": 30.0,
    "checkin_interval_wifi_s": 1.0,
    "checkin_interval_mesh_s": 15.0,
    "checkin_payload": {
      "latitude": 0.0,
      "longitude": 0.0
    },
    "track_update_min_distance_m": 25.0,
    "track_update_min_seconds": 5.0
  }
}
```

---

### `sensors` - Sensor Manager
**Version:** 1.0.0  
**Purpose:** Run sensor workers that combine capture + analysis  

**Capabilities:**
- Load sensor worker plugins from config
- Start/stop workers with the OS lifecycle
- Publish analyzed outputs on `sensor.output`
- Publish command intents on `sensor.command` for registered device commands

**Dependencies:** None  

**Configuration:**
```json
{
  "sensors": {
    "enabled": true,
    "devices": [
      {
        "id": "camera-front",
        "type": "camera_bearing",
        "enabled": true,
        "interval_s": 1.0,
        "bearing_deg": 0.0,
        "elevation_deg": 0.0,
        "confidence": 0.5,
        "commands": ["slew_turret"]
      }
    ]
  }
}
```

---

### `data_store` - Data Store Manager
**Version:** 1.0.0  
**Purpose:** General-purpose in-memory store with optional persistence  

**Capabilities:**
- Store keyed records by namespace
- Publish updates and snapshots on the bus
- Optional JSON persistence to disk

**Dependencies:** None  

**Configuration:**
```json
{
  "data_store": {
    "enabled": true,
    "persistence": {
      "enabled": false,
      "path": "~/.atlas_data_store.json",
      "interval_s": 30.0,
      "persist_on_change": false
    }
  }
}
```

**Bus Topics:**
- Publish `data_store.put` `{namespace, key, value, meta}`
- Publish `data_store.get` `{namespace, key, request_id}`
- Publish `data_store.list` `{namespace, request_id}`
- Publish `data_store.delete` `{namespace, key}`
- Publish `data_store.snapshot.request` `{namespace?, request_id}`
- Subscribe `data_store.response` `{namespace, key?, keys?, record?, request_id}`
- Subscribe `data_store.updated` `{namespace, key, record}`
- Subscribe `data_store.deleted` `{namespace, key, record}`
- Subscribe `data_store.snapshot` `{snapshot, request_id}`

---

## Contributing

When adding a new module:

1. Create a module directory: `modules/<module_name>/`
2. Add `manager.py` with a `ModuleBase` subclass
3. Define `MODULE_NAME`, `MODULE_VERSION`, `DEPENDENCIES`
4. Implement `start()` and `stop()` methods
5. Document bus topics (publishes/subscribes)
6. Add configuration schema to this catalog
7. Add tests to `tests/unit/test_<module_name>.py`

---

*Last updated: 2025-01-14*
