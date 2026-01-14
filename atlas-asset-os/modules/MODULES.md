# ATLAS Asset OS Module Catalog

This catalog documents all modules available in the ATLAS Asset OS ecosystem, including production modules, work-in-progress modules, and planned modules.

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

## Planned Modules

### `gps_module` - GPS Module
**Status:** Planned  
**Purpose:** GPS parsing and position reporting  

**Capabilities:**
- GPS receiver communication (UART/USB)
- NMEA sentence parsing
- Position, altitude, heading reporting
- Satellite lock monitoring
 - Time synchronization
 
**Dependencies:** None
 
---
 
### `navigation` - Navigation
**Status:** Planned  
**Purpose:** GPS coordinate handling and waypoint management  

**Capabilities:**
- Distance and bearing calculations
- Waypoint queue management
- Target approach detection
 - Coordinate transforms (WGS84, UTM)
 
**Dependencies:** `gps_module` (optional, can receive position from other sources)
 
---
 
### `mission_planner` - Mission Planner
**Status:** Planned  
**Purpose:** Mission execution and survey pattern generation  

**Capabilities:**
- Waypoint queue management
- Mission state machine (idle, running, paused, aborted, complete)
- Survey pattern generation (grid, lawnmower, orbit)
- Mission progress tracking
 - Task completion callbacks
 
**Dependencies:** `navigation`, `flight_controller`
  
---
 
### `power_manager` - Power Manager
**Status:** Planned  
**Purpose:** Battery and power system monitoring  

**Capabilities:**
- Battery voltage, current, percentage monitoring
- Low-voltage warning triggers
- Flight time estimation
- Solar panel monitoring (for solar-powered assets)
 - Power state reporting
 
**Dependencies:** None
  
---
 
### `failsafe_manager` - Failsafe Manager
**Status:** Planned  
**Purpose:** Failsafe behavior coordination  

**Capabilities:**
- Signal loss detection and RTL
- Low-battery failsafe triggers
- Geofence violation handling
 - Emergency landing coordination
 
**Dependencies:** `comms`, `power_manager`, `flight_controller`
  
---
 
### `storage_manager` - Storage Manager
**Status:** Planned  
**Purpose:** Disk space and file management  

**Capabilities:**
- Disk space monitoring
- File rotation/deletion policies
- Upload queue management
 - Storage status reporting
 
**Dependencies:** None
  
---
 
### `image_uploader` - Image Uploader
**Status:** Planned  
**Purpose:** Upload images and videos to Atlas Command  

**Capabilities:**
- Upload images/videos as Objects to Atlas Command
- Create media_refs on entities
- Batch upload for efficiency
- Upload queue management
 - Retry failed uploads
 
**Dependencies:** `comms`, `storage_manager`
  
---
 
### `telemetry_aggregator` - Telemetry Aggregator
**Status:** Planned  
**Purpose:** Batch telemetry data for efficient transmission  

**Capabilities:**
- Collect telemetry from various modules
- Time-based batching
- Threshold-based immediate transmission
- Data compression
 - Upload to Atlas Command
 
**Dependencies:** `comms`
  
---
 
### `button_handler` - Button Handler
**Status:** Planned  
**Purpose:** Emergency/SOS button handling  

**Capabilities:**
- Button press detection
- Debouncing
- Emergency alert broadcasting
 - Button status reporting
 
**Dependencies:** None
  
---
 
## Module Dependency Graph

```
                    ┌─────────────┐
                    │  comms     │ (all)
                    └──────┬──────┘
                           │
                           ├──────────┬────────────┐
                           │          │            │
                    ┌──────▼──────┐    ┌───▼────┐
                    │ operations  │    │ image_  │
                    │            │    │ uploader│
                    └─────────────┘    └────┬────┘
                           │                │
                    ┌──────▼──────┐  ┌─────▼──────┐
                    │ health_     │  │ storage_   │
                    │ monitor     │  │ manager    │
                    └─────────────┘  └────────────┘

                    ┌─────────────────────────────┐
                    │ power_manager             │ (battery-powered)
                    └──────┬──────────────────┘
                           │
                    ┌──────▼──────┐
                    │ telemetry_   │
                    │ aggregator  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ flight_     │ (drone)
                    │ controller  │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                     │
       ┌──────▼──────┐      ┌─────▼──────┐
       │ navigation   │      │ failsafe_   │
       │             │      │ manager     │
       └──────┬──────┘      └─────┬──────┘
              │                     │
       ┌──────▼──────┐      ┌─────▼──────┐
       │ mission_    │      │            │
       │ planner     │      │            │
       └─────────────┘      └────────────┘

              ┌──────┐
              │ gps_ │ (tracker)
              │module│
              └──────┘

              ┌────────────┐
              │ camera_   │ (camera, drone)
              │ module    │
              └────────────┘
```

---

## Module Usage by Asset Type

| Module | Tracker | Camera | Drone |
|--------|---------|---------|-------|
| comms | ✓ | ✓ | ✓ |
| operations | ✓ | ✓ | ✓ |
| health_monitor | ✓ | ✓ | ✓ |
| power_manager | ✓ | ✓ | ✓ |
| gps_module | ✓ | (opt) | (via FC) |
| telemetry_aggregator | ✓ | - | ✓ |
| camera_module | - | ✓ | ✓ |
| storage_manager | - | ✓ | - |
| image_uploader | - | ✓ | ✓ |
| flight_controller | - | - | ✓ |
| navigation | - | - | ✓ |
| mission_planner | - | - | ✓ |
| failsafe_manager | - | - | ✓ |
| button_handler | (opt) | - | - |

---

## Contributing

When adding a new module:

1. Create a module directory: `modules/<module_name>/`
2. Add `manager.py` with a `ModuleBase` subclass
3. Define `MODULE_NAME`, `MODULE_VERSION`, `DEPENDENCIES`
4. Implement `start()` and `stop()` methods
5. Document bus topics (publishes/subscribes)
6. Add configuration schema to this catalog
7. Update module usage table and dependency graph
8. Add tests to `tests/unit/test_<module_name>.py`

---

*Last updated: 2025-01-14*
