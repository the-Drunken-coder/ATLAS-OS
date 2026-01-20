#!/usr/bin/env python3
"""
Demonstration script for the system check functionality.

This script shows how to trigger a system check and view the results.
"""

import logging
import sys
import time
from pathlib import Path

# Add ATLAS_ASSET_OS to path
asset_os_root = Path(__file__).resolve().parent
sys.path.insert(0, str(asset_os_root))

from framework.master import OSManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Simple test configuration
TEST_CONFIG = {
    "atlas": {
        "base_url": "http://localhost:8000",
        "api_token": None,
        "asset": {
            "id": "demo-asset-001",
            "name": "Demo Asset",
            "model_id": "demo-model",
        },
    },
    "modules": {
        "comms": {"enabled": True, "simulated": True, "gateway_node_id": "!demo123"},
        "operations": {"enabled": True, "heartbeat_interval_s": 30.0},
        "data_store": {"enabled": True},
        "sensors": {"enabled": True, "devices": []},
    },
}


def main():
    """Run the demonstration."""
    print("=" * 80)
    print("ATLAS Asset OS - System Check Demonstration")
    print("=" * 80)
    print()

    # Create OS manager
    print("Initializing OS Manager...")
    os_manager = OSManager(config=TEST_CONFIG)

    # Discover and start modules
    print("Discovering modules...")
    os_manager.module_loader.discover_modules()
    
    print("Resolving dependencies...")
    os_manager.module_loader.resolve_dependencies()
    
    print("Loading modules...")
    os_manager.module_loader.load_modules()
    
    print("Starting modules...")
    os_manager.module_loader.start_modules()

    # Give modules time to fully start
    print("Waiting for modules to start...")
    time.sleep(1.0)

    print()
    print("-" * 80)
    print("Running System Check...")
    print("-" * 80)
    print()

    # Run system check directly
    results = os_manager.module_loader.run_system_check(timeout_s=5.0)

    # Display results
    print("System Check Results:")
    print()
    print(f"Overall Health: {'✓ HEALTHY' if results['overall_healthy'] else '✗ UNHEALTHY'}")
    print()
    print("Module Status:")
    print()

    for module_name, module_result in results["modules"].items():
        healthy = module_result.get("healthy", False)
        status = module_result.get("status", "unknown")
        health_icon = "✓" if healthy else "✗"
        
        print(f"  {health_icon} {module_name:15s} - {status}")
        
        # Print additional diagnostic info
        for key, value in module_result.items():
            if key not in {"healthy", "status"}:
                print(f"      {key}: {value}")
        print()

    print()
    print("-" * 80)
    print("Testing Bus-Based System Check Request...")
    print("-" * 80)
    print()

    # Set up listener for response
    response_data = {"received": False, "data": None}

    def handle_response(data):
        response_data["received"] = True
        response_data["data"] = data
        print("Received system check response via bus!")

    os_manager.bus.subscribe("system.check.response", handle_response)

    # Trigger system check via bus (as operations would)
    print("Publishing system.check.request...")
    os_manager.bus.publish("system.check.request", {"request_id": "demo-123"})

    # Wait for response
    time.sleep(0.5)

    if response_data["received"]:
        data = response_data["data"]
        print()
        print("Response received with:")
        print(f"  - Request ID: {data.get('request_id')}")
        print(f"  - Timestamp: {data.get('timestamp')}")
        print(f"  - Overall Healthy: {data['results']['overall_healthy']}")
    else:
        print("No response received (this shouldn't happen!)")

    print()
    print("-" * 80)
    print("Stopping modules...")
    print("-" * 80)
    print()

    # Clean up
    os_manager.module_loader.stop_modules()

    print()
    print("=" * 80)
    print("Demonstration Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
