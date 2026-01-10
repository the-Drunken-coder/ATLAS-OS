import sys
import os
import time
import json
import logging
import threading
from pathlib import Path
from typing import Optional

# --- Path Setup ---
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]  # Up to ATLAS root

# Local bridge and http client (though not used directly here, but good for consistency)
BRIDGE_SRC = REPO_ROOT / "Atlas_Command" / "connection_packages" / "atlas_meshtastic_bridge" / "src"
if BRIDGE_SRC.exists() and str(BRIDGE_SRC) not in sys.path:
    sys.path.insert(0, str(BRIDGE_SRC))

# Add modules to path so we can import .modules.comms
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# --- LED Abstraction ---
try:
    from gpiozero import LED
    HAS_GPIO = True
except (ImportError, Exception):
    HAS_GPIO = False
    class LED:
        def __init__(self, pin):
            self.pin = pin
            self.value = 0
            logging.info(f"[MOCK] Initialized LED on pin {pin}")
        @property
        def is_lit(self):
            return self.value == 1
        def on(self):
            self.value = 1
            logging.info(f"[MOCK] LED on pin {self.pin} is ON")
        def off(self):
            self.value = 0
            logging.info(f"[MOCK] LED on pin {self.pin} is OFF")
        def toggle(self):
            self.value = 1 - self.value
            logging.info(f"[MOCK] LED on pin {self.pin} is {'ON' if self.is_lit else 'OFF'}")

# --- Comms Manager ---
from modules.comms.manager import CommsManager

class RangeTester:
    def __init__(self, config_path: Path):
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # GPIO Setup
        self.green_led = LED(self.config.get("green_led_pin", 17))
        self.red_led = LED(self.config.get("red_led_pin", 27))
        
        # Mock bus for CommsManager
        class MockBus:
            def subscribe(self, topic, handler): pass
            def publish(self, topic, data): pass
            
        self.bus = MockBus()
        self.comms = CommsManager(self.bus, {"modules": {"comms": self.config}})
        self.running = False

    def _load_config(self, path: Path) -> dict:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
            return {}

    def setup_logging(self):
        log_level = getattr(logging, str(self.config.get("log_level", "INFO")).upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        self.logger = logging.getLogger("RangeTester")

    def flash_startup(self):
        """Flash LEDs on startup to indicate boot."""
        self.logger.info("Flashing LEDs for startup...")
        for _ in range(3):
            self.green_led.on()
            self.red_led.on()
            time.sleep(0.2)
            self.green_led.off()
            self.red_led.off()
            time.sleep(0.2)

    def start(self):
        self.logger.info("Starting Range Tester...")
        
        # Flash LEDs on startup
        self.flash_startup()
        
        self.comms.start()
        
        # Give it a second to initialize the bridge
        time.sleep(2)
        
        if self.comms.client:
            self.logger.info("Comms client ready.")
        else:
            self.logger.error("Comms client failed to initialize!")

        self.running = True
        
        # Initial state: Red ON (waiting for first ping)
        self.red_led.on()
        self.green_led.off()

        try:
            while self.running:
                self.check_range()
                time.sleep(self.config.get("ping_interval", 10))
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.logger.info("Stopping Range Tester...")
        self.running = False
        self.comms.stop()
        self.green_led.off()
        self.red_led.off()

    def check_range(self):
        if not self.comms.client:
            self.logger.warning("Comms client not ready")
            self.red_led.on()
            self.green_led.off()
            return

        self.logger.info(f"Pinging gateway: {self.config.get('gateway_node_id')}")
        try:
            # Using the direct client call for simplicity in this dedicated script
            # BasePlate_OS uses functions registry, but we can call client directly
            result = self.comms.client.test_echo(
                message="ping",
                timeout=15,
                max_retries=1
            )
            
            # If result is not None, we assume it's a success (ACK received)
            if result:
                self.logger.info("Gateway responded! Range is GOOD.")
                self.green_led.on()
                self.red_led.off()
                self.logger.info(f"LED state: green={self.green_led.value}, red={self.red_led.value}")
            else:
                self.logger.warning("Gateway timeout. Range is UNKNOWN/BAD.")
                self.green_led.off()
                self.red_led.on()
                self.logger.info(f"LED state: green={self.green_led.value}, red={self.red_led.value}")
                
        except Exception as e:
            self.logger.error(f"Error checking range: {e}")
            self.green_led.off()
            self.red_led.on()

if __name__ == "__main__":
    tester = RangeTester(CURRENT_DIR / "config.json")
    tester.start()
