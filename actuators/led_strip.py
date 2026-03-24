# led_strip.py
# Actuator module for Wi-Fi LED strip control using flux_led
#
# Author: Francesco Urru
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/CPSA_2026
# License: MIT

import threading
import time
from typing import Optional, Tuple, List

import flux_led
from flux_led import BulbScanner

from utils.logger import log_system
from utils.config import get_led_strip_config
from utils.lock import device_reconnection_lock

# Device scanning function

def scan_led_devices(timeout: int = 5) -> List[str]:
    """
    Scans for Wi-Fi LED devices using flux_led and returns their IP addresses.

    Args:
        timeout (int): Duration of the network scan in seconds.

    Returns:
        List[str]: A list of IP addresses corresponding to discovered LED devices.
    """
    log_system(f"[LED Scanner] Starting WiFi scan for {timeout} seconds...")
    ip_list: List[str] = []

    try:
        scanner = BulbScanner()
        devices = scanner.scan(timeout)

        for device in devices:
            ipaddr = device.get('ipaddr')
            model = device.get('model')
            if ipaddr:
                log_system(f"[LED Scanner] Found device: {ipaddr} (model: {model})")
                ip_list.append(ipaddr)

        if not ip_list:
            log_system("[LED Scanner] No LED devices found.", level="WARNING")

    except Exception as exc:
        log_system(f"[LED Scanner] Scan error: {exc}", level="ERROR")

    return ip_list

#LedStripThread

class LedThread(threading.Thread):
    """
    Thread for managing a Wi-Fi LED strip using flux_led.

    Args:
        ip_address (str): The IP address of the target LED strip.
    """

    def __init__(self, ip_address: str):
        super().__init__(daemon=True)
        self.ip_address = ip_address

        self._stop_event = threading.Event()
        self._event = threading.Event()
        self._disconnect_event = threading.Event()

        self._pattern: Optional[int] = None
        self._color: Optional[Tuple[int, int, int, int]] = None
        self._speed: int = 100
        self._intensity: int = 100
        self._off_timer = None
        self._pending_duration_ms = 0

        self._bulb: Optional[flux_led.WifiLedBulb] = None

        cfg = get_led_strip_config()
        self._fast_retry_attempts = int(cfg.get("fast_retry_attempts", 5))
        self._retry_interval = int(cfg.get("retry_interval", 5))
        self._retry_sleep = int(cfg.get("retry_sleep", 60))
        self._duration = int(cfg.get("duration", 5000))

    def run(self) -> None:
        log_system(f"[LedStrip: {self.ip_address}] Thread started")
        self._connect()
        self._wait_for_event()

    def _wait_for_event(self) -> None:
        while not self._stop_event.is_set():
            if self._event.wait(timeout=0.5):
                self._event.clear()

                if self._disconnect_event.is_set():
                    self._disconnect_event.clear()
                    with device_reconnection_lock:
                        self._reconnection_attempts()

                if self._bulb:
                    self._process_action()

        if self._bulb:
            self._turn_off()

    def _connect(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._bulb = flux_led.WifiLedBulb(self.ip_address)
                self._bulb.refreshState()
                self._connection_feedback()
                log_system(f"[LedStrip: {self.ip_address}] Connected successfully")
                return
            except Exception as exc:
                log_system(f"[LedStrip: {self.ip_address}] Connection error: {exc}", level="ERROR")
                time.sleep(self._retry_interval)

    def _connection_feedback(self) -> None:
        try:
            self._bulb.setRgbw(0, 0, 0, 255, brightness=50)
            time.sleep(0.3)
            self._bulb.setRgbw(0, 0, 0, 0)
            time.sleep(0.2)
            self._bulb.setRgbw(0, 0, 0, 255, brightness=50)
            time.sleep(0.3)
            self._bulb.setRgbw(0, 0, 0, 0)
        except Exception:
            pass

    def _reconnection_attempts(self) -> None:
        log_system(f"[LedStrip: {self.ip_address}] Starting reconnection attempts...")

        for attempt in range(1, self._fast_retry_attempts + 1):
            if self._stop_event.is_set():
                return
            if self._try_reconnect():
                return
            log_system(f"[LedStrip: {self.ip_address}] Fast retry {attempt}/{self._fast_retry_attempts} failed", level="WARNING")
            time.sleep(self._retry_interval)

        log_system(f"[LedStrip: {self.ip_address}] Switching to slow retries every {self._retry_sleep}s", level="WARNING")
        while not self._stop_event.is_set():
            if self._try_reconnect():
                return
            log_system(f"[LedStrip: {self.ip_address}] Slow retry failed", level="WARNING")
            time.sleep(self._retry_sleep)

    def _try_reconnect(self) -> bool:
        try:
            self._bulb = flux_led.WifiLedBulb(self.ip_address)
            self._bulb.refreshState()
            self._connection_feedback()
            log_system(f"[LedStrip: {self.ip_address}] Reconnected successfully")
            return True
        except Exception:
            return False

    def execute(
        self,
        *,
        pattern: Optional[int] = None,
        color: Optional[Tuple[int, int, int, int]] = None,
        intensity: int = 100,
        speed: int = 100,
        duration: Optional[int] = None,
    ) -> None:
        """Trigger an effect or solid color on the LED strip."""
        self._pattern = pattern
        # Clamp color channels to 0..255
        if color is not None:
            try:
                r, g, b, w = color
                r = max(0, min(int(r), 255))
                g = max(0, min(int(g), 255))
                b = max(0, min(int(b), 255))
                w = max(0, min(int(w), 255))
                self._color = (r, g, b, w)
            except Exception:
                self._color = None
        else:
            self._color = None

        self._intensity = max(0, min(intensity, 100))
        self._speed = max(1, min(speed, 100))
        self._pending_duration_ms = self._duration if duration is None else max(0, int(duration))
        self._event.set()

    def _process_action(self) -> None:
        try:
            if self._color:
                r, g, b, w = self._color
                if self._intensity <= 0 or (r==0 and g==0 and b==0 and w==0):
                    self._turn_off()
                    return
                log_system(f"[LedStrip: {self.ip_address}] Setting color ({r},{g},{b},{w}) intensity={self._intensity}%")
                self._bulb.setRgbw(r, g, b, w, brightness=self._intensity)
                self._schedule_off_timer(self._pending_duration_ms)
            elif self._pattern is not None:
                if self._intensity <= 0:
                    self._turn_off()
                log_system(f"[LedStrip: {self.ip_address}] Setting pattern {self._pattern} speed={self._speed}% intensity={self._intensity}%")
                self._bulb.set_effect(effect=self._pattern, speed=self._speed, brightness=self._intensity)
                self._schedule_off_timer(self._pending_duration_ms)

        except Exception as exc:
            log_system(f"[LedStrip: {self.ip_address}] Action error: {exc}", level="ERROR")
            self._disconnect_event.set()
            self._event.set()

    def _turn_off(self) -> None:
        try:
            if self._bulb:
                try:
                    self._bulb.turnOff()
                except Exception as e:
                    log_system(f"[LedStrip: {self.ip_address}] turnOff() failed: {e}")
                try:
                    self._bulb.setRgbw(0,0,0,0, brightness=0)
                except Exception:
                    pass
                log_system(f"[LedStrip: {self.ip_address}] Turned off")
        except Exception as exc:
            log_system(f"[LedStrip: {self.ip_address}] TurnOff error: {exc}", level="ERROR")

    def stop(self) -> None:
        self._stop_event.set()
        self._event.set()
        try:
            if self._off_timer:
                self._off_timer.cancel()
        except Exception:
            pass
        if threading.current_thread() is not self and self.is_alive():
            self.join()
        log_system(f"[LedStrip: {self.ip_address}] Thread stopped")

    def _schedule_off_timer(self, ms:int) -> None:
        try:
            if self._off_timer:
                self._off_timer.cancel()
        except Exception:
            pass
        self._off_timer = None
        if ms > 0 and not self._stop_event.is_set():
            self._off_timer = threading.Timer(ms/1000.0, self._auto_off)
            self._off_timer.daemon = True
            self._off_timer.start()

    def _auto_off(self) -> None:
        if self._stop_event.is_set():
            return
        try:
            if self._bulb:
                self._bulb.turnOff()
                log_system(f"[LedStrip: {self.ip_address}] Auto OFF")
        except Exception as e:
            log_system(f"[LedStrip: {self.ip_address}] Auto OFF error: {e}", level="WARNING")
