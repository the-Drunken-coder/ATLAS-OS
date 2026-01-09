#!/usr/bin/env python3
"""
Comms module test harness for BasePlate_OS_Next.

Starts a MessageBus + CommsManager (client mode) and lets you inject requests onto
the central bus to exercise Meshtastic bridge commands. Responses from the comms
module are printed when received on the bus.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import inspect
from pathlib import Path
from typing import Any, Dict

# Locate BasePlate_OS_Next
HERE = Path(__file__).resolve()
BASE_OS_DIR = HERE.parents[3] / "BasePlate_OS_Next"
if str(BASE_OS_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_OS_DIR))

from bus import MessageBus  # type: ignore  # noqa: E402
from modules.comms.manager import CommsManager  # type: ignore  # noqa: E402
from modules.comms.functions import FUNCTION_REGISTRY  # type: ignore  # noqa: E402

LOG = logging.getLogger("comms_injector")


def load_config() -> Dict[str, Any]:
    cfg_path = BASE_OS_DIR / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"BasePlate_OS_Next config.json not found at {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return raw if isinstance(raw, dict) else {}


def _parse_value(raw: str) -> Any:
    lower = raw.strip().lower()
    if lower in {"none", "null"}:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return raw


def prompt_args(fn_name: str, func: Any) -> Dict[str, Any]:
    """Prompt for args based on the function signature (skipping the client param)."""
    sig = inspect.signature(func)
    args: Dict[str, Any] = {}
    for name, param in list(sig.parameters.items())[1:]:  # skip client
        default = param.default
        has_default = default is not inspect._empty
        while True:
            prompt = f"{name}"
            if has_default and default is not inspect._empty:
                prompt += f" [default: {default!r}]"
            prompt += ": "
            raw = input(prompt).strip()
            if not raw:
                if has_default and default is not inspect._empty:
                    # use function default by omitting arg
                    break
                else:
                    print(f"{name} is required")
                    continue
            try:
                args[name] = _parse_value(raw)
                break
            except Exception as exc:
                print(f"Invalid value for {name}: {exc}")
                continue
    return args


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_config()
    LOG.info("Loaded BasePlate_OS_Next config from %s", BASE_OS_DIR / "config.json")

    bus = MessageBus()

    # Start comms manager (client mode) using config/modules/comms settings
    comms_mgr = CommsManager(bus, config)
    comms_mgr.start()

    # Subscribe to responses
    def on_response(data: Any) -> None:
        LOG.info("Response: %s", json.dumps(data, indent=2, default=str))

    bus.subscribe("comms.response", on_response)

    available = sorted(FUNCTION_REGISTRY.keys())
    LOG.info("Available comms functions: %s", ", ".join(available))

    try:
        while True:
            print("\n[Comms Injector] Enter function name (or 'list'/'q'):")
            fn = input("> ").strip()
            if not fn:
                continue
            if fn.lower() in {"q", "quit", "exit"}:
                break
            if fn.lower() == "list":
                print("Functions:", ", ".join(available))
                continue
            if fn not in FUNCTION_REGISTRY:
                print(f"Unknown function '{fn}'. Type 'list' to see options.")
                continue
            args = prompt_args(fn, FUNCTION_REGISTRY[fn])
            req_id = f"req-{int(time.time()*1000)}"
            payload = {"function": fn, "args": args, "request_id": req_id}
            LOG.info("Publishing comms.request: %s", payload)
            bus.publish("comms.request", payload)
    except KeyboardInterrupt:
        LOG.info("Interrupted; shutting down")
    finally:
        comms_mgr.stop()
        bus.shutdown()


if __name__ == "__main__":
    main()
