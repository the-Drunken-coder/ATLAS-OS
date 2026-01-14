# ATLAS Asset OS Module Catalog

This catalog documents all modules available in the ATLAS Asset OS ecosystem, including production modules and work-in-progress modules.

---

## Production Modules

### `comms` - Communications Manager
**Version:** 1.0.0  
**Purpose:** Meshtastic radio bridge for Atlas Command communication  

**Capabilities:**
- Radio connection management (auto-discovery, reconnection)
- Message sending and receiving
- Function registry for Atlas Command API calls
- Reliability strategies (retry, acknowledgment)
 - Spooling for offline message handling
 
**Dependencies:** None  
 
**Configuration:**
```json
{
  "comms": {
    "enabled": true,
    "simulated": false,
    "gateway_node_id": "gateway",
    "radio_port": "auto",
    "mode": "general",
    "spool_path": "~/.baseplate_comm_spool.json"
  }
}
```

---

### `operations` - Operations Manager
**Version:** 1.0.0  
**Purpose:** Message routing, heartbeat, and command handling  

**Capabilities:**
- Route incoming messages to appropriate topics
- Publish periodic heartbeat (every 30s)
- Command/request/data/error message type classification
 - Forward commands to command handlers
 
**Dependencies:** `comms`  
 
**Configuration:**
```json
{
  "operations": {
    "enabled": true
  }
}
```

---

## Work In Progress (WIP)

### `health_monitor` - Health Monitor
**Status:** WIP  
**Purpose:** System health aggregation and reporting  

**Capabilities:**
- Monitor CPU usage, memory usage, storage space
- Monitor temperature
- Battery status aggregation (for battery-powered assets)
- System anomaly detection
 - Periodic health reporting to Atlas Command via entity health component
 
**Dependencies:** None (optional: `power_manager`)

---

### `camera_module` - Camera & Computer Vision
**Status:** WIP  
**Purpose:** Camera control and computer vision processing  

**Capabilities:**
- Camera initialization and control (USB, Pi camera, IP camera)
- Image capture (still photos)
- Video recording and streaming
- Camera settings management (resolution, FPS, exposure, gain)
- Object detection (person, vehicle, animal detection)
- Bounding box tracking
 - Frame buffer for computer vision pipeline
 
**Dependencies:** None (optional: `image_uploader` for uploading captures)

---

### `flight_controller` - Flight Controller Interface
**Status:** WIP  
**Purpose:** MAVLink communication with flight controllers (Pixhawk, etc.)  

**Capabilities:**
- MAVLink connection to autopilot (serial or UDP)
- Flight mode management (AUTO, LOITER, RTL, GUIDED, STABILIZE)
- Arm/disarm control
- Send waypoint commands to autopilot
- Receive telemetry from autopilot (position, attitude, velocity, battery)
- Send position commands (for guided mode navigation)
- Heartbeat monitoring
 - System status and alerts reception
 
**Dependencies:** None

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
