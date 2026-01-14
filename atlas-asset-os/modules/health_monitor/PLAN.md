# Health Monitor Module Plan

## Goal
- Collect and aggregate core system vitals (CPU, memory, disk, temperature) for local use. Battery status is aggregated and reported by health_monitor **only** from metrics provided by the flight controller module; health_monitor must not probe battery hardware directly. Hold data internally and expose it on demand; only emit warnings to the bus when thresholds are crossed.

## Initial Scope
- Collect baseline metrics on Linux SBCs (psutil + platform-specific temps) and cache them locally.
- Provide on-demand reads for current snapshot and recent aggregates (e.g., rolling averages).
- Optional anomaly flags (threshold breaches) stored alongside metrics; emit warning events on the bus when thresholds are crossed. Do not stream raw metrics periodically on the bus; periodic health reporting to Atlas Command (via the entity health component) is handled as summarized health state, not raw metric firehose.

## Milestones
- [ ] Define manager skeleton with config schema and request/response bus topics for snapshot + aggregate reads, plus warning topic.
- [ ] Implement metric collectors with graceful degradation when sensors are missing.
- [ ] Add in-memory store (current + rolling window) with basic aggregation helpers.
- [ ] Add optional anomaly tagging (threshold rules) that is queryable and emits warning events when crossed; no periodic streaming of raw metrics on the bus, while allowing summarized periodic health reporting via the entity health component if configured.
- [ ] Tests for collectors, storage/aggregation, request handlers, and warning emission.

## Open Questions
- Threshold defaults for warning events?
