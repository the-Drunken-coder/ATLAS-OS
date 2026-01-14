# Flight Controller Module Plan

## Goal
- Single point of contact to MAVLink autopilots (Pixhawk, etc.) for mode control, arming, telemetry ingest, and guided movement commands. No other module should talk directly to the flight controller; they consume data/commands via this module's bus interface.

## Initial Scope
- Autodetect MAVLink transport (serial/UDP) with reconnect handling.
- Mode management (GUIDED/LOITER/AUTO/RTL) and arm/disarm control.
- Telemetry subscription for position/attitude/velocity **and battery** -> bus topics.
- Battery management: normalize MAVLink battery data, surface SOC/voltage/alerts for other modules (e.g., health monitor, power manager).
- Waypoint + position setpoint helpers for guided navigation (primary command set).
- Heartbeat monitor with safety timeouts and basic alerting.

## Milestones
- [ ] Define manager skeleton, config schema, and bus topics (telemetry, commands, alerts, battery feed) targeting ArduPilot common dialect.
- [ ] Implement connection handler with retry/backoff and link health metrics.
- [ ] Add mode/arming APIs and validation gates.
- [ ] Implement telemetry pump + converters to common schema, including normalized battery payload.
- [ ] Add waypoint command helpers (primary command set) with ack handling.
- [ ] Tests for connection flows, mode transitions, telemetry parsing, and battery normalization.

## Open Questions
- Minimum telemetry set for Atlas Command compatibility?
