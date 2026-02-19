#!/usr/bin/env python3
"""ATLAS Antenna Demo — main loop.

Reads GPS, checks in with Atlas Command, handles get_signal_strength commands.
"""

import json
import logging
import time
import uuid
from pathlib import Path

from antenna import AntennaReader
from comms import CommsClient
from geo import destination_point
from gps import GpsReader

log = logging.getLogger("antenna_demo")


def load_config():
    path = Path(__file__).resolve().parent / "config.json"
    with open(path) as f:
        return json.load(f)


def handle_task(task, gps, antenna, comms, cfg):
    """Route a task to the right handler."""
    task_id = task.get("task_id")
    components = task.get("components") or {}
    extra = task.get("extra") or {}
    parameters = components.get("parameters") or {}
    # Resolve command identifier: prefer components.command.type (standard format),
    # then fall back to parameters.command or extra.command_definition_id
    cmd_component = components.get("command") or {}
    command = (cmd_component.get("type") if isinstance(cmd_component, dict) else None) \
               or components.get("command_name") \
               or parameters.get("command") \
               or extra.get("command_definition_id") \
               or task_id

    if command == "get_signal_strength":
        comms.start_task(task_id)
        try:
            result = do_get_signal_strength(gps, antenna, comms, cfg)
            comms.complete_task(task_id, result)
            log.info("Task %s completed: %.1f dBm → %s",
                     task_id, result["signal_strength_dbm"], result["track_entity_id"])
        except Exception as exc:
            comms.fail_task(task_id, str(exc))
            log.error("Task %s failed: %s", task_id, exc)
    else:
        log.warning("Unknown command '%s' in task %s", command, task_id)
        comms.fail_task(task_id, f"Unknown command: {command}")


def do_get_signal_strength(gps, antenna, comms, cfg):
    """Read signal, calculate forward point, create track entity."""
    # 1 — read signal
    signal = antenna.read_signal()
    if signal is None:
        raise RuntimeError("No signal strength reading available")

    # 2 — get position
    pos = gps.get_position()
    if pos is None:
        raise RuntimeError("No GPS fix available")

    heading = pos.get("heading_deg") or 0.0
    offset = cfg.get("track_offset_m", 12.192)

    # 3 — calculate forward point
    track_lat, track_lon = destination_point(
        pos["latitude"], pos["longitude"], heading, offset
    )

    # 4 — create track entity
    prefix = cfg.get("track_alias_prefix", "sig-track")
    track_id = f"{prefix}-{uuid.uuid4().hex[:8]}"

    result = comms.create_entity(
        entity_id=track_id,
        entity_type="track",
        subtype=cfg.get("track_subtype", "signal"),
        alias=track_id,
        components={
            "telemetry": {
                "latitude": track_lat,
                "longitude": track_lon,
            },
            "custom_signal_data": {
                "signal_strength_dbm": signal,
                "source_asset": cfg["asset"]["id"],
                "source_latitude": pos["latitude"],
                "source_longitude": pos["longitude"],
                "source_heading_deg": heading,
                "offset_m": offset,
            },
        },
    )
    if result is None:
        raise RuntimeError(f"Failed to create track entity '{track_id}'")

    return {
        "signal_strength_dbm": signal,
        "track_entity_id": track_id,
        "track_position": {"latitude": track_lat, "longitude": track_lon},
        "source_position": {
            "latitude": pos["latitude"],
            "longitude": pos["longitude"],
            "heading_deg": heading,
        },
        "offset_m": offset,
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = load_config()
    log.info("ATLAS Antenna Demo starting")

    gps = GpsReader(cfg["gps"])
    antenna = AntennaReader(cfg["antenna"])
    comms = CommsClient(cfg["comms"], cfg["asset"], cfg.get("radio"))

    gps.start()
    comms.connect()

    comms.register_asset(supported_commands=["get_signal_strength"])

    checkin_interval = cfg.get("checkin_interval_s", 15)
    last_checkin = 0.0

    log.info("Running — checkin every %ds, Ctrl+C to stop", checkin_interval)

    try:
        while True:
            now = time.time()

            if now - last_checkin >= checkin_interval:
                pos = gps.get_position()
                if pos:
                    tasks = comms.checkin(pos)
                    for task in tasks:
                        handle_task(task, gps, antenna, comms, cfg)
                else:
                    log.debug("Skipping check-in — no GPS fix yet")
                last_checkin = now

            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        gps.stop()
        comms.close()


if __name__ == "__main__":
    main()
