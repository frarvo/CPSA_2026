# metamotion.py
# Actuator module for vibration control using MetaMotionRL BLE device
#
# Author: Francesco Urru
# Github: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

######

import threading
import time
from mbientlab.metawear import MetaWear, libmetawear
from mbientlab.warble import WarbleException
from utils.config import get_metamotion_config
from utils.logger import log_system
from bluepy.btle import Scanner

from utils.lock import device_reconnection_lock


def scan_metamotion_devices(timeout: int) -> list[str]:
    """
    Scans for nearby MetaMotion BLE devices and returns their MAC addresses.

    Args:
        timeout (int): Duration of the BLE scan in seconds.

    Returns:
        List[str]: A list of MAC addresses (strings) corresponding to MetaWear devices.
    """
    cfg = get_metamotion_config() or {}
    timeout = int(cfg.get('scan_timeout',5)) if timeout is None else int(timeout)

    log_system(f"[MetaMotion Scanner] Starting BLE scan for {timeout} seconds...")
    mac_list = []
    try:
        scanner = Scanner()
        devices = scanner.scan(timeout)
    except Exception as e:
        log_system(f"[MetaMotion Scanner] Scan error: {e}", level="ERROR")
        return []

    for dev in devices:
        name = dev.getValueText(9)  # 9 = Complete Local Name
        if name == "MetaWear":
            log_system(f"[MetaMotion Scanner] Found MetaWear at {dev.addr}")
            mac_list.append(dev.addr)

    if not mac_list:
        log_system("[MetaMotion Scanner] No MetaWear devices found.", level="WARNING")

    return mac_list

class MetaMotionThread(threading.Thread):
    """
    Thread for managing BLE connection and vibration control on a MetaMotion device.

    This thread:
    - Connects to a MetaMotion device using a known MAC address
    - Waits for external vibration commands
    - Handles automatic disconnection and reconnection
    - Executes motor vibration with configurable intensity and duration

    Attributes:
        mac_address (str): BLE MAC address of the target device
        vibration_duty (int): Intensity of the motor (0-100)
        vibration_time (int): Duration in milliseconds
    """

    def __init__(self, mac_address: str):
        """
        Initializes the MetaMotionThread with a specific BLE MAC address
        :param mac_address: (str) The BLE MAC address of the MetaMotion device
        """
        super().__init__(daemon=True)
        self.mac_address = mac_address
        self.stop_event = threading.Event()
        self.event = threading.Event()
        self.disconnect_event = threading.Event()
        self.vibration_duty = 100
        self.vibration_time = 500
        self.device = None
        self.vibration_lock = threading.Lock()
        cfg = get_metamotion_config() or {}

        self.fast_retry_attempts = int(cfg.get("fast_retry_attempts", 10))
        self.retry_interval = int(cfg.get("retry_interval", 5))
        self.retry_sleep = int(cfg.get("retry_sleep", 60))

    def run(self):
        """
        Main thread entry point. Connects to the MetaMotion device and enters the main event loop.
        :return:
        """
        log_system(f"[MetaMotion: {self.mac_address}] Thread started")
        self._connect_meta_device()
        self._wait_for_event()

    def _connect_meta_device(self):
        """
        Attempts to establish a BLE connection to the MetaMotion device using the stored MAC address.
        On success, sets up a disconnection callback and performs connection feedback.
        :return:
        """
        addr = self.mac_address
        self.device = MetaWear(addr)
        self.device.on_disconnect = lambda status: self._on_disconnection(status)

        while not getattr(self.device, "is_connected", False):
            if self.stop_event.is_set():
                return
            try:
                self.device.connect()
                time.sleep(1)
            except WarbleException as e:
                log_system(f"[MetaMotion: {addr}] Connection failed: {e}", level="ERROR")
                time.sleep(self.retry_interval)

        log_system(f"[MetaMotion: {addr}] Connected successfully")
        self._connection_feedback()

    def _connection_feedback(self):
        """
        Executes a brief double vibration sequence to confirm successful connection to the device.
        :return:
        """
        try:
            libmetawear.mbl_mw_haptic_start_motor(self.device.board, 100, 200)
            time.sleep(0.250)
            libmetawear.mbl_mw_haptic_start_motor(self.device.board, 100, 200)
            time.sleep(1)
        except Exception:
            # Doesn't raise exception during shutdown
            pass

    def _wait_for_event(self):
        """
        Main loop that waits for external vibration commands or disconnection events.
        Processes vibration requests and handles reconnection when needed.
        :return:
        """
        while not self.stop_event.is_set():
            if self.event.wait(timeout=0.5):
                self.event.clear()

                if self.disconnect_event.is_set():
                    self.disconnect_event.clear()
                    with device_reconnection_lock:
                        self._reconnection_attempts()

                if self.device and getattr(self.device, "is_connected", False):
                    self._process_vibration()

        if self.device and getattr(self.device, "is_connected", False):
            self._disconnect_device()

    def _process_vibration(self):
        """
        Triggers the vibration motor using the current duty cycle and duration time.
        :return:
        """
        try:
            if self.device and getattr(self.device, "is_connected", False):
                with self.vibration_lock:
                    duty = max(0, min(int(self.vibration_duty), 100))
                    duration = max(1, int(self.vibration_time))
                log_system(f"[MetaMotion: {self.mac_address}] Vibrating {duration}ms at {duty}%")
                libmetawear.mbl_mw_haptic_start_motor(self.device.board, duty, duration)
        except Exception:
            pass

    def set_vibration(self, duty_cycle: int, time_ms: int):
        """
        Set the vibration parameters and signals the thread to process the request.
        :param duty_cycle: (int) Vibration intensity.
        :param time_ms: (int) Duration of the vibration in milliseconds.
        :return:
        """
        with self.vibration_lock:
            self.vibration_duty = duty_cycle
            self.vibration_time = time_ms
        self.event.set()

    def stop(self):
        """
        Stops the thread, disconnects the device if connected, and waits for termination.
        :return:
        """
        self.stop_event.set()
        self.event.set()
        # Prevent callbacks during shutdown
        try:
            if self.device:
                self.device.on_disconnect = None
        except Exception:
            pass

        if threading.current_thread() is not self and self.is_alive():
            self.join()
        log_system(f"[MetaMotion: {self.mac_address}] Thread stopped.")

    def _disconnect_device(self):
        """
        Safely disconnects the MetaMotion device if it is currently connected.
        :return:
        """
        try:
            if self.device:
                # Disable callbacks before disconnect to avoid teardown races
                try:
                    self.device.on_disconnect = None
                except Exception:
                    pass

                if getattr(self.device, "is_connected", False):
                    self.device.disconnect()
                    log_system(f"[MetaMotion: {self.mac_address}] Disconnected manually")

        except Exception as e:
            log_system(f"[MetaMotion: {self.mac_address}] Disconnection error: {e}", level="ERROR")

    def _on_disconnection(self, status):
        """
        Callback invoked by the MetaMotion API when the device disconnects.
        :param status:
        :return:
        """
        if status != 0:
            log_system(f"[MetaMotion: {self.mac_address}] Disconnected unexpectedly (status = {status})", level="WARNING")
            self.disconnect_event.set()
            self.event.set()
        else:
            log_system(f"[MetaMotion: {self.mac_address}] Disconnected successfully.")

    def execute(self, **kwargs):
        """
        Triggers the MetaMotion vibration motor with provided parameters.

        :param kwargs:
            duty (int): Motor intensity (default: 100)
            duration (int): Duration in milliseconds (default: 500)
        :return:
        """
        duty = kwargs.get("duty", 100)
        duration = kwargs.get("duration", 500)
        self.set_vibration(duty, duration)

    def _reconnection_attempts(self):
        """
        Attempts to reconnect to the MetaMotion device using a fast-retry strategy first, followed by
        a slower retry loop until reconnection succeeds or stop_event is set.
        :return:
        """
        log_system(f"[MetaMotion: {self.mac_address}] Starting reconnection procedure.")

        # Recreate the device object
        self.device = MetaWear(self.mac_address)
        self.device.on_disconnect = lambda status: self._on_disconnection(status)

        # Phase 1: fast retries
        for attempt in range(self.fast_retry_attempts):
            if self.stop_event.is_set():
                return
            try:
                self.device.connect()
                log_system(f"[MetaMotion: {self.mac_address}] Reconnected successfully.")
                self._connection_feedback()
                return
            except Exception as e:
                log_system(f"[MetaMotion: {self.mac_address}] Retry {attempt + 1}/{self.fast_retry_attempts} failed: {e}", level="ERROR")
                for _ in range(self.retry_interval):
                    if self.stop_event.is_set():
                        return
                    time.sleep(1)

        # Phase 2: slow retries
        log_system(f"[MetaMotion: {self.mac_address}] All fast retries failed. Sleeping for {self.retry_sleep}s before retrying.")
        while not self.stop_event.is_set():
            try:
                self.device.connect()
                log_system(f"[MetaMotion: {self.mac_address}] Reconnected successfully.")
                try:
                    self._connection_feedback()
                except Exception:
                    pass
                return
            except Exception as e:
                log_system(f"[MetaMotion: {self.mac_address}] Slow retry failed: {e}", level="WARNING")
                for _ in range(self.retry_interval):
                    if self.stop_event.is_set():
                        return
                    time.sleep(1)