#!/usr/bin/env python3
"""Start the ATLAS Asset OS.

Usage:
    python start.py [config_path]
    
    If config_path is not provided, looks for config.json in the same folder as this script.
"""

import sys
import argparse
import logging
from pathlib import Path

# Set up paths
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from framework.master import OSManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Start ATLAS Asset OS")
    parser.add_argument("config", nargs="?", type=Path, help="Path to config.json file")
    args = parser.parse_args()
    
    # Determine config path - use script's folder config by default
    if args.config:
        config_path = args.config
    else:
        config_path = _SCRIPT_DIR / "config.json"
    
    if not config_path.exists():
        print(f"ERROR: config.json not found at {config_path}")
        sys.exit(1)
    
    os_manager = OSManager(config_path=config_path)
    os_manager.run()


if __name__ == "__main__":
    main()
