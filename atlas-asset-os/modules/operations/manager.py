import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from modules.operations.geo import haversine_meters

# Module base is in the same modules/ directory
from modules.module_base import ModuleBase  # noqa: E402
from modules.operations.registration import register_asset  # noqa: E402

LOGGER = logging.getLogger("modules.operations")


class OperationsManager(ModuleBase):
    """Operations manager for message routing and heartbeat."""

    MODULE_NAME = "operations"
    MODULE_VERSION = "1.0.0"
    DEPENDENCIES: List[str] = ["comms"]  # Depends on comms module

    def __init__(self, bus, config):
        super().__init__(bus, config)
        self._thread: Optional[threading.Thread] = None
        ops_cfg = self.get_module_config()
        self._heartbeat_interval_s = float(ops_cfg.get("heartbeat_interval_s", 30.0))
        self._checkin_interval_default_s = float(
            ops_cfg.get("checkin_interval_s", 30.0)
        )
        self._checkin_interval_wifi_s = float(
            ops_cfg.get("checkin_interval_wifi_s", 1.0)
        )
        self._checkin_interval_mesh_s = float(
            ops_cfg.get("checkin_interval_mesh_s", 15.0)
        )
        raw_payload = ops_cfg.get("checkin_payload") or {}
        allowed_keys = {
            "latitude",
            "longitude",
            "altitude_m",
            "speed_m_s",
            "heading_deg",
        }
        self._checkin_payload = {
            key: value
            for key, value in raw_payload.items()
            if key in allowed_keys and value is not None
        }
        self._last_heartbeat = 0.0
        self._last_checkin = 0.0
        self._checkin_disabled_logged = False
        self._current_method: Optional[str] = None
        self._current_checkin_interval_s = self._checkin_interval_default_s
        self._registration_started = False
        self._registration_complete = False
        self._checkin_payload_logged = False
        self._checkin_waiting_logged = False
        self._data_store_sync_interval_s = 1.0
        self._last_data_store_sync = 0.0
        self._last_snapshot_request_id: Optional[str] = None
        self._track_namespace = str(ops_cfg.get("track_namespace", "tracks"))
        self._track_update_min_distance_m = float(
            ops_cfg.get("track_update_min_distance_m", 25.0)
        )
        self._track_update_min_seconds = float(
            ops_cfg.get("track_update_min_seconds", 5.0)
        )
        self._track_last_sent: dict[str, dict[str, float]] = {}
        self._data_store_namespaces = [self._track_namespace]
        self._command_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self._command_queue: Deque[dict[str, Any]] = deque()
        self._command_lock = threading.Lock()
        self._active_command: Optional[dict[str, Any]] = None
        self._known_task_ids: set[str] = set()

    def start(self) -> None:
        self._logger.info("Starting Operations Manager")
        self.running = True

        # Subscribe to bus events
        self.bus.subscribe("comms.message_received", self._handle_comms_message)
        self.bus.subscribe("comms.method_changed", self._handle_method_changed)
        self.bus.subscribe("data_store.snapshot", self._handle_data_store_snapshot)
        self.bus.subscribe("comms.response", self._handle_comms_response)
        self.bus.subscribe("commands.register", self._handle_command_register)
        self.bus.subscribe("commands.unregister", self._handle_command_unregister)
        self.bus.subscribe("system.check.request", self._handle_system_check_request)

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._logger.info("Stopping Operations Manager")
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self):
        """Main operations loop."""
        while self.running:
            now = time.time()

            # Heartbeat at reduced frequency
            if now - self._last_heartbeat >= self._heartbeat_interval_s:
                self.bus.publish("operations.heartbeat", {"status": "ok"})
                self._last_heartbeat = now

            # Periodic check-in to Atlas Command (disabled if interval <= 0)
            if (
                self._current_checkin_interval_s > 0
                and now - self._last_checkin >= self._current_checkin_interval_s
            ):
                asset_cfg = (
                    self.config.get("atlas", {}).get("asset", {})
                    if isinstance(self.config, dict)
                    else {}
                )
                entity_id = asset_cfg.get("id")
                if not entity_id:
                    if not self._checkin_disabled_logged:
                        self._logger.warning(
                            "Check-in disabled: missing atlas.asset.id in config"
                        )
                        self._checkin_disabled_logged = True
                elif not self._registration_complete:
                    if not self._checkin_waiting_logged:
                        self._logger.info(
                            "Check-in waiting for asset registration to complete"
                        )
                        self._checkin_waiting_logged = True
                elif not self._checkin_payload:
                    if not self._checkin_payload_logged:
                        self._logger.warning(
                            "Check-in disabled: operations.checkin_payload is empty"
                        )
                        self._checkin_payload_logged = True
                else:
                    self.bus.publish(
                        "comms.request",
                        {
                            "function": "checkin_entity",
                            "args": {
                                "entity_id": entity_id,
                                "status_filter": "pending,in_progress",
                                **self._checkin_payload,
                            },
                            "request_id": f"checkin-{int(now * 1000)}",
                        },
                    )
                    self._last_checkin = now

            if (
                self._data_store_sync_interval_s > 0
                and now - self._last_data_store_sync >= self._data_store_sync_interval_s
            ):
                self._last_data_store_sync = now
                request_id = f"data-store-{int(now * 1000)}"
                self._last_snapshot_request_id = request_id
                namespaces = self._data_store_namespaces
                if namespaces:
                    for namespace in namespaces:
                        self.bus.publish(
                            "data_store.snapshot.request",
                            {"namespace": namespace, "request_id": request_id},
                        )
                else:
                    self.bus.publish(
                        "data_store.snapshot.request",
                        {"request_id": request_id},
                    )

            self._maybe_dispatch_command()
            time.sleep(1)

    def _handle_comms_message(self, data):
        """Handle messages received from the outside world."""
        if not data or not isinstance(data, dict):
            self._logger.warning("Invalid message structure received: %s", data)
            return

        # Extract message fields
        msg_type = data.get("type", "unknown")
        command = data.get("command", "unknown")
        message_id = data.get("message_id", "unknown")
        msg_data = data.get("data", {})
        sender = data.get("sender")

        self._logger.info(
            "Received message via comms: sender=%s, type=%s, command=%s, id=%s",
            sender,
            msg_type,
            command,
            message_id[:8] if message_id != "unknown" else "unknown",
        )

        # Route message to appropriate topic based on type
        if msg_type == "request":
            # Incoming command/request
            self.bus.publish(
                "operations.command_received",
                {
                    "sender": sender,
                    "command": command,
                    "message_id": message_id,
                    "data": msg_data,
                    "timestamp": data.get("timestamp", time.time()),
                },
            )
        elif msg_type == "response":
            # Response to a previous request
            self.bus.publish(
                "operations.data_received",
                {
                    "sender": sender,
                    "command": command,
                    "message_id": message_id,
                    "data": msg_data,
                    "correlation_id": data.get("correlation_id"),
                    "timestamp": data.get("timestamp", time.time()),
                },
            )
        elif msg_type == "error":
            # Error message
            self.bus.publish(
                "operations.error_received",
                {
                    "sender": sender,
                    "command": command,
                    "message_id": message_id,
                    "data": msg_data,
                    "correlation_id": data.get("correlation_id"),
                    "timestamp": data.get("timestamp", time.time()),
                },
            )
        else:
            # Unknown type, log and publish to generic topic
            self._logger.warning("Unknown message type '%s' received", msg_type)
            self.bus.publish(
                "operations.message_received",
                {
                    "sender": sender,
                    "type": msg_type,
                    "command": command,
                    "message_id": message_id,
                    "data": msg_data,
                    "timestamp": data.get("timestamp", time.time()),
                },
            )

    def _handle_comms_response(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        if data.get("function") != "checkin_entity":
            return
        if not data.get("ok"):
            return
        result = data.get("result")
        if not isinstance(result, dict):
            return
        tasks = result.get("tasks")
        if not isinstance(tasks, list):
            return
        for task in tasks:
            self._enqueue_task(task)

    def _handle_command_register(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        command = data.get("command")
        handler = data.get("handler")
        if not command or not callable(handler):
            return
        self._command_handlers[str(command)] = handler
        self._publish_task_catalog()

    def _handle_command_unregister(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        command = data.get("command")
        if not command:
            return
        self._command_handlers.pop(str(command), None)
        self._publish_task_catalog()

    def _publish_task_catalog(self) -> None:
        asset_cfg = (
            self.config.get("atlas", {}).get("asset", {})
            if isinstance(self.config, dict)
            else {}
        )
        entity_id = asset_cfg.get("id")
        if not entity_id:
            return
        supported = sorted(self._command_handlers.keys())
        components = {"task_catalog": {"supported_tasks": supported}}
        self.bus.publish(
            "comms.request",
            {
                "function": "update_entity",
                "args": {"entity_id": entity_id, "components": components},
                "request_id": f"task-catalog-{int(time.time() * 1000)}",
            },
        )

    def _enqueue_task(self, task: dict) -> None:
        if not isinstance(task, dict):
            return
        task_id = task.get("task_id")
        if not task_id:
            return
        status = str(task.get("status", "pending")).lower()
        if status not in {"pending", "in_progress"}:
            return
        task_id = str(task_id)
        if task_id in self._known_task_ids:
            return
        # Use explicit command from parameters if provided, otherwise fall back to task_id
        command = task_id
        components_raw = task.get("components")
        components = components_raw if isinstance(components_raw, dict) else {}
        parameters_raw = components.get("parameters")
        parameters = parameters_raw if isinstance(parameters_raw, dict) else {}
        command_param = parameters.get("command")
        if command_param:
            command = str(command_param)
        elif components.get("command_name"):
            command = str(components.get("command_name"))
        if command not in self._command_handlers:
            # Attempt to notify the control plane that the task has failed due to an unknown command.
            # Only mark the task as known after we have successfully published the fail_task request.
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    self.bus.publish(
                        "comms.request",
                        {
                            "function": "fail_task",
                            "args": {
                                "task_id": task_id,
                                "error_message": "No handler registered for command",
                            },
                        },
                    )
                    self._known_task_ids.add(task_id)
                    break
                except Exception:
                    LOGGER.exception(
                        "Failed to publish fail_task for unknown command (task_id=%s), attempt %d/%d",
                        task_id,
                        attempt + 1,
                        max_attempts,
                    )
                    if attempt < max_attempts - 1:
                        time.sleep(1)
            return
        with self._command_lock:
            self._known_task_ids.add(task_id)
            self._command_queue.append(
                {
                    "task_id": task_id,
                    "command": command,
                    "parameters": parameters,
                    "skip_start": status == "in_progress",
                }
            )

    def _maybe_dispatch_command(self) -> None:
        with self._command_lock:
            if self._active_command is not None:
                return
            if not self._command_queue:
                return
            task = self._command_queue.popleft()
            self._active_command = task
        threading.Thread(
            target=self._execute_command, args=(task,), daemon=True
        ).start()

    def _execute_command(self, task: dict) -> None:
        task_id_raw = task.get("task_id")
        task_id = str(task_id_raw) if task_id_raw is not None else None
        command_raw = task.get("command")
        command = str(command_raw) if command_raw is not None else ""
        parameters_raw = task.get("parameters")
        parameters: dict[str, Any] = (
            parameters_raw if isinstance(parameters_raw, dict) else {}
        )
        handler = self._command_handlers.get(command)
        if handler is None:
            self._finalize_command(
                task_id, success=False, error="No handler registered"
            )
            return
        if not task.get("skip_start"):
            self.bus.publish(
                "comms.request",
                {"function": "start_task", "args": {"task_id": task_id}},
            )
        try:
            result = handler(parameters)
        except Exception as exc:
            self._finalize_command(task_id, success=False, error=str(exc))
            return
        self._finalize_command(task_id, success=True, result=result)

    def _finalize_command(
        self,
        task_id: Optional[str],
        *,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        if not task_id:
            return
        if success:
            args: dict[str, Any] = {"task_id": task_id}
            if isinstance(result, dict):
                args["result"] = result
            self.bus.publish(
                "comms.request", {"function": "complete_task", "args": args}
            )
        else:
            self.bus.publish(
                "comms.request",
                {
                    "function": "fail_task",
                    "args": {"task_id": task_id, "error_message": error},
                },
            )
        with self._command_lock:
            self._active_command = None

    def _handle_method_changed(self, data):
        if not isinstance(data, dict):
            return
        method = data.get("method")
        if not method or method == self._current_method:
            return

        self._current_method = method
        if method == "wifi":
            self._current_checkin_interval_s = self._checkin_interval_wifi_s
        elif method == "meshtastic":
            self._current_checkin_interval_s = self._checkin_interval_mesh_s
        else:
            self._current_checkin_interval_s = self._checkin_interval_default_s

        # Calculate appropriate next check-in time based on elapsed time and new interval
        now = time.time()
        elapsed_since_last = now - self._last_checkin

        # If the new interval is shorter and we've already exceeded it, check in immediately
        # Otherwise, preserve timing to avoid redundant check-ins
        if self._current_checkin_interval_s < elapsed_since_last:
            # Switching to faster method and already past the interval
            self._last_checkin = now - self._current_checkin_interval_s
        # else: keep _last_checkin as-is to maintain check-in cadence

        self._logger.info(
            "Comms method set to %s; check-in interval %.1fs",
            method,
            self._current_checkin_interval_s,
        )

        if not self._registration_started:
            self._registration_started = True

            def _register():
                self._registration_complete = register_asset(self.bus, self.config)

            threading.Thread(target=_register, daemon=True).start()

    def _handle_data_store_snapshot(self, data):
        if not isinstance(data, dict):
            return
        request_id = data.get("request_id")
        if (
            self._last_snapshot_request_id
            and request_id != self._last_snapshot_request_id
        ):
            return
        snapshot = data.get("snapshot")
        if not isinstance(snapshot, dict):
            return
        self._sync_tracks_from_snapshot(snapshot)
        self.bus.publish(
            "operations.data_store_sync",
            {"snapshot": snapshot, "request_id": request_id, "timestamp": time.time()},
        )

    def _sync_tracks_from_snapshot(self, snapshot):
        tracks = snapshot.get(self._track_namespace)
        if not isinstance(tracks, dict):
            return
        for track_id, record in tracks.items():
            if not isinstance(record, dict):
                continue
            value = record.get("value")
            if not isinstance(value, dict):
                continue
            lat = value.get("latitude")
            lon = value.get("longitude")
            if lat is None or lon is None:
                continue
            try:
                lat_val = float(lat)
                lon_val = float(lon)
            except (TypeError, ValueError):
                continue
            self._maybe_broadcast_track(str(track_id), value, lat_val, lon_val)

    def _maybe_broadcast_track(
        self, track_id: str, value: dict, lat: float, lon: float
    ) -> None:
        now = time.time()
        last = self._track_last_sent.get(track_id)
        if last:
            elapsed = now - last.get("ts", 0.0)
            if elapsed < self._track_update_min_seconds:
                return
            distance = haversine_meters(
                lat, lon, last.get("lat", lat), last.get("lon", lon)
            )
            if distance < self._track_update_min_distance_m:
                return
        args = {"entity_id": track_id, "latitude": lat, "longitude": lon}
        if value.get("altitude_m") is not None:
            args["altitude_m"] = value.get("altitude_m")
        if value.get("speed_m_s") is not None:
            args["speed_m_s"] = value.get("speed_m_s")
        if value.get("heading_deg") is not None:
            args["heading_deg"] = value.get("heading_deg")
        self.bus.publish(
            "comms.request",
            {
                "function": "update_telemetry",
                "args": args,
                "request_id": f"track-{track_id}-{int(now * 1000)}",
            },
        )
        self._track_last_sent[track_id] = {"lat": lat, "lon": lon, "ts": now}

    def _handle_system_check_request(self, data: dict) -> None:
        """
        Handle system check requests.

        Publishes system.check.response with the results.
        """
        self._logger.info("Running system check")
        # Publish request to get module loader to run checks
        self.bus.publish("module_loader.system_check.request", data)

    def system_check(self) -> Dict[str, Any]:
        """
        Run diagnostics on the operations module.

        Returns:
            Dictionary with diagnostic results.
        """
        # Check basic health
        healthy = self.running and self._thread is not None and self._thread.is_alive()

        result = {
            "healthy": healthy,
            "status": "running" if healthy else "not_running",
            "heartbeat_interval_s": self._heartbeat_interval_s,
            "checkin_interval_s": self._current_checkin_interval_s,
            "registration_complete": self._registration_complete,
            "active_command": self._active_command is not None,
            "queued_commands": len(self._command_queue),
        }

        return result
