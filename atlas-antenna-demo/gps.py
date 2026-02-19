"""GPS reader — simulated walk or real NMEA serial."""

import logging
import math
import threading
import time

log = logging.getLogger(__name__)


class GpsReader:
    """Continuously reads GPS and exposes the latest position."""

    def __init__(self, config):
        self._simulated = config.get("simulated", True)
        self._port = config.get("serial_port", "/dev/ttyUSB0")
        self._baud = int(config.get("baud_rate", 9600))
        self._interval = float(config.get("interval_s", 1.0))

        # Sim settings
        self._sim_lat = float(config.get("sim_start_lat", 34.0522))
        self._sim_lon = float(config.get("sim_start_lon", -118.2437))
        self._sim_heading = float(config.get("sim_heading_deg", 45.0))
        self._sim_speed = float(config.get("sim_speed_m_s", 1.4))

        # Latest position (None until first fix)
        self.position = None
        self._lock = threading.Lock()
        self._thread = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def get_position(self):
        with self._lock:
            return dict(self.position) if self.position else None

    # ── internal ──────────────────────────────────────────────

    def _update(self, lat, lon, heading):
        with self._lock:
            self.position = {
                "latitude": lat,
                "longitude": lon,
                "heading_deg": heading,
            }

    def _run(self):
        if self._simulated:
            self._run_sim()
        else:
            self._run_hardware()

    def _run_sim(self):
        log.info("GPS sim: start=(%.6f,%.6f) hdg=%.0f spd=%.1f m/s",
                 self._sim_lat, self._sim_lon, self._sim_heading, self._sim_speed)
        R = 6_371_008.8
        lat, lon = self._sim_lat, self._sim_lon

        while self._running:
            d = self._sim_speed * self._interval
            br = math.radians(self._sim_heading)
            lat_r, lon_r = math.radians(lat), math.radians(lon)
            ang = d / R

            lat2 = math.asin(
                math.sin(lat_r) * math.cos(ang)
                + math.cos(lat_r) * math.sin(ang) * math.cos(br)
            )
            lon2 = lon_r + math.atan2(
                math.sin(br) * math.sin(ang) * math.cos(lat_r),
                math.cos(ang) - math.sin(lat_r) * math.sin(lat2),
            )
            lat, lon = math.degrees(lat2), math.degrees(lon2)
            self._update(lat, lon, self._sim_heading)
            time.sleep(self._interval)

    def _run_hardware(self):
        try:
            import serial
            import pynmea2
        except ImportError:
            log.error("Install pynmea2 + pyserial for hardware GPS")
            return

        log.info("GPS hw: port=%s baud=%d", self._port, self._baud)
        heading = None

        try:
            with serial.Serial(self._port, self._baud, timeout=self._interval) as ser:
                while self._running:
                    try:
                        line = ser.readline().decode("ascii", errors="replace").strip()
                        if not line:
                            continue
                        msg = pynmea2.parse(line)
                        if isinstance(msg, pynmea2.GGA) and msg.latitude and msg.longitude:
                            self._update(msg.latitude, msg.longitude, heading)
                        elif isinstance(msg, pynmea2.RMC):
                            if msg.true_course is not None:
                                heading = float(msg.true_course)
                            if msg.latitude and msg.longitude and msg.status == "A":
                                self._update(msg.latitude, msg.longitude, heading)
                    except (pynmea2.ParseError, UnicodeDecodeError):
                        continue
        except Exception as exc:
            log.error("GPS serial error: %s", exc)
