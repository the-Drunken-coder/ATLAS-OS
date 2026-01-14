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

**Bus Topics:**
- Publishes: `comms.message_received`, `comms.connection_lost`, `comms.connection_restored`, `comms.response`
- Subscribes to: `comms.send_message`, `comms.request`

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

**Bus Topics:**
- Publishes: `operations.heartbeat`, `operations.command_received`, `operations.data_received`, `operations.error_received`, `operations.message_received`
- Subscribes to: `comms.message_received`

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

**Bus Topics:**
- Publishes: `health.status`
- Subscribes to: `power_manager.status` (if available)

**Dependencies:** None (optional: `power_manager`)

**Configuration (planned):**
```json
{
  "health_monitor": {
    "enabled": true,
    "report_interval_s": 60,
    "thresholds": {
      "cpu_warning_pct": 80,
      "memory_warning_pct": 85,
      "storage_warning_pct": 90,
      "temperature_warning_c": 70
    }
  }
}
```

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

**Bus Topics:**
- Publishes: `camera.image_captured`, `camera.video_frame`, `camera.status`, `cv.objects_found`
- Subscribes to: `camera.capture_image`, `camera.start_stream`, `camera.stop_stream`, `camera.configure`

**Dependencies:** None (optional: `image_uploader` for uploading captures)

**Configuration (planned):**
```json
{
  "camera_module": {
    "enabled": true,
    "device": "/dev/video0",
    "resolution": "1920x1080",
    "fps": 30,
    "stream_enabled": false,
    "auto_capture": false,
    "capture_interval_s": 60,
    "object_detection": {
      "enabled": true,
      "model": "yolov5n",
      "confidence_threshold": 0.6,
      "detect_classes": ["person", "car", "truck", "animal"]
    }
  }
}
```

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

**Bus Topics:**
- Publishes: `flight.telemetry` (position, attitude, velocity, battery), `flight.status`, `flight.alerts`, `flight.mode_changed`
- Subscribes to: `flight.set_mode`, `flight.arm`, `flight.disarm`, `flight.set_waypoint`, `flight.set_position`

**Dependencies:** None

**Configuration (planned):**
```json
{
  "flight_controller": {
    "enabled": true,
    "connection": "serial:/dev/ttyACM0:57600",
    "system_id": 1,
    "component_id": 1,
    "baudrate": 57600,
    "heartbeat_timeout_s": 5,
    "target_system": 1,
    "target_component": 1
  }
}
```

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

**Bus Topics:**
- Publishes: `gps.position`, `gps.status`, `gps.satellites`
- Subscribes to: `gps.request_position`

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

**Bus Topics:**
- Publishes: `nav.position`, `nav.target_reached`, `nav.distance_to_target`
- Subscribes to: `nav.calculate_distance`, `nav.add_waypoint`, `nav.clear_waypoints`

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

**Bus Topics:**
- Publishes: `mission.status`, `mission.waypoint_complete`, `mission.complete`
- Subscribes to: `mission.start`, `mission.pause`, `mission.resume`, `mission.abort`

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

**Bus Topics:**
- Publishes: `power.status`, `power.low_battery_warning`
- Subscribes to: `power.read_status`

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

**Bus Topics:**
- Publishes: `failsafe.triggered`, `failsafe.cleared`
- Subscribes to: `comms.connection_lost`, `power.low_battery_warning`

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

**Bus Topics:**
- Publishes: `storage.status`, `storage.low_space`
- Subscribes to: `storage.check_space`, `storage.rotate_files`

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

**Bus Topics:**
- Publishes: `image_upload.status`, `image_upload.complete`
- Subscribes to: `camera.image_captured`, `camera.video_segment`

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

**Bus Topics:**
- Publishes: `telemetry.batch`
- Subscribes to: `flight.telemetry`, `gps.position`, `power.status`

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

**Bus Topics:**
- Publishes: `button.pressed`, `button.status`
- Subscribes to: `button.test`

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
