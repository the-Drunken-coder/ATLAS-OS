"""Antenna signal-strength reader — simulated random or real serial."""

import logging
import random

log = logging.getLogger(__name__)


class AntennaReader:
    """Reads signal strength on demand."""

    def __init__(self, config):
        self._simulated = config.get("simulated", True)
        self._port = config.get("serial_port", "/dev/ttyUSB1")
        self._baud = int(config.get("baud_rate", 115200))

        rng = config.get("sim_signal_range", [-80, -40])
        self._sim_min = float(rng[0])
        self._sim_max = float(rng[1])

        if self._simulated:
            log.info("Antenna sim: range=[%.0f, %.0f] dBm", self._sim_min, self._sim_max)
        else:
            log.info("Antenna hw: port=%s baud=%d", self._port, self._baud)

    def read_signal(self):
        """Return signal strength in dBm, or None on failure."""
        if self._simulated:
            return random.uniform(self._sim_min, self._sim_max)
        return self._read_hardware()

    def _read_hardware(self):
        """Placeholder serial protocol: send READ, expect RSSI:<value>.

        Adapt this method to match your actual antenna hardware.
        """
        try:
            import serial
        except ImportError:
            log.error("Install pyserial for hardware antenna")
            return None

        try:
            with serial.Serial(self._port, self._baud, timeout=2) as ser:
                ser.write(b"READ\n")
                resp = ser.readline().decode("ascii", errors="replace").strip()
                if resp.startswith("RSSI:"):
                    return float(resp[5:])
                log.warning("Unexpected antenna response: %s", resp)
        except Exception as exc:
            log.error("Antenna read error: %s", exc)
        return None
