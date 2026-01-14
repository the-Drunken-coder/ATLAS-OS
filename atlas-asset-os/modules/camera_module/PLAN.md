# Camera Module Plan

## Goal
- Provide camera control plus a minimal CV pipeline for captures, recordings, and basic detections.

## Initial Scope
- Support USB/Pi/IP camera init with configurable resolution/FPS.
- Still capture and short video recording to disk; optional live stream hook.
- Lightweight detection path (person/vehicle/animal) with bounding boxes.
- Frame buffer abstraction that other modules (e.g., uploader) can consume.

## Milestones
- [ ] Define manager skeleton, config schema, and bus topics for capture/stream events.
- [ ] Implement camera lifecycle (init, start/stop capture, teardown) with retries.
- [ ] Add capture/record APIs and storage path policy.
- [ ] Integrate minimal detection model path + metadata packaging.
- [ ] Tests for camera selection, capture flows, and detection metadata.

## Open Questions
- Preferred detection backend (OpenCV DNN vs. ONNX runtime) and model size constraints?
- Target output formats for uploads/streams (jpeg, mp4/h264)?
