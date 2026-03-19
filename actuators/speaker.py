# speaker.py
# Actuator module for Bluetooth speaker control and audio playback.
#
# Author: Francesco Urru
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

import threading
import subprocess
import time
from pathlib import Path
from playsound import playsound
from utils.logger import log_system
from utils.config import get_speaker_config
from utils.audio_paths import AudioLibrary
from utils.lock import device_reconnection_lock



def scan_speaker_devices(timeout: int) -> list[str]:
    """
    Scans for nearby Bluetooth speakers using bluetoothctl and returns a list of MAC addresses.

    This function launches a bluetoothctl session, enables scanning for a set duration,
    retrieves visible devices, and filters them by known audio profiles such as
    'icon: audio' or 'audio sink'.

    Args:
        timeout (int): Duration of the scan in seconds.

    Returns:
        List[str]: A list of MAC addresses corresponding to compatible audio devices.
    """
    cfg = get_speaker_config() or {}
    timeout = int(cfg.get("scan_timeout", 5)) if timeout is None else int(timeout)

    log_system(f"[Speaker Scanner] Starting Bluetooth scan for {timeout} seconds...")
    mac_list = []

    process = None

    try:
        # Start scan session with bluetoothctl
        process = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        process.stdin.write("scan on\n")
        process.stdin.flush()

        time.sleep(timeout)

        process.stdin.write("scan off\n")
        process.stdin.flush()
        time.sleep(1)

        # Retrieve all discovered devices
        result = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")

        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                mac = parts[1]
                info = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout.lower()

                name_line = next((l for l in info.splitlines() if "name:" in l), "")
                device_name = name_line.split("name:")[-1].strip() if name_line else ""
                if ("icon: audio" in info or "audio sink" in info) and device_name.startswith("muse_speaker"):
                    log_system(f"[Speaker Scanner] Audio device found: {mac}")
                    mac_list.append(mac)

        if not mac_list:
            log_system("[Speaker Scanner] No compatible speakers found.", level="WARNING")

        return mac_list

    except Exception as e:
        log_system(f"[Speaker Scanner] Scan error: {e}", level="ERROR")
        return []

    finally:
        if process:
            try:
                process.stdin.close()
                process.terminate()
                process.wait()
            except Exception:
                pass

class SpeakerThread(threading.Thread):
    """
    Thread for managing Bluetooth speaker connection and audio playback.

    This thread:
    - Maintains a persistent Bluetooth connection with a known device
    - Auto-reconnects if the speaker becomes unavailable
    - Waits for external commands to play local audio files
    - Can be stopped gracefully from external code

    Attributes:
        mac_address (str): MAC address of the Bluetooth speaker
    """

    def __init__(self, mac_address: str):
        """
        Initializes the speaker thread and its synchronization primitives.
        :param mac_address: (str) MAC address of the Bluetooth speaker
        """
        super().__init__(daemon=True)
        self.mac_address = mac_address
        self.event = threading.Event()
        self.stop_event = threading.Event()
        self.file = None
        self.connected = False
        cfg = get_speaker_config() or {}

        self.fast_retry_attempts = int(cfg.get("fast_retry_attempts", 5))
        self.retry_interval = int(cfg.get("retry_interval", 5))
        self.retry_sleep = int(cfg.get("retry_sleep", 60))

    def run(self):
        """
        Main loop that ensures connection is maintained and audio playback is triggered when requested.
        """
        log_system(f"[Speaker: {self.mac_address}] Thread started")

        while not self.stop_event.is_set():
            is_conn = self._is_connected()
            self.connected = is_conn
            if not is_conn:
                with device_reconnection_lock:
                    self._reconnection_attempts()
                # Refresh status after each attempt
                self.connected = self._is_connected()

            if self.event.is_set() and self.connected:
                try:
                    if self.file:
                        p = Path(self.file)
                        if p.exists():
                            # Check stop and connection before playing to avoid blocking
                            if not self.stop_event.is_set() and self._is_connected():
                                log_system(f"[Speaker: {self.mac_address}] Playing audio: {p}")
                                playsound(str(p))
                            else:
                                log_system(f"[Speaker: {self.mac_address}] Skipping playback (stopping or disconnected)", level="WARNING")
                        else:
                            log_system(f"[Speaker: {self.mac_address}] File not found or invalid: {self.file}", level="WARNING")
                    else:
                        log_system(f"[Speaker: {self.mac_address}] No audio file provided", level="WARNING")
                except Exception as e:
                    log_system(f"[Speaker: {self.mac_address}] Error during audio playback: {e}", level="ERROR")
                finally:
                    self.event.clear()

            time.sleep(1)

        self._disconnect()

    def execute(self, **kwargs):
        """
        Triggers playback of a local audio file on the connected speaker.

        Keyword Args:
            file (str): Path to the audio file to play
        """
        file = kwargs.get("file")
        if not file:
            log_system(f"[Speaker: {self.mac_address}] No audio file provided", level="WARNING")
            return
        self.file = file
        self.event.set()

    def stop(self):
        """
        Stops the thread and disconnects from the speaker.
        """
        self.stop_event.set()
        self.event.set()
        if threading.current_thread() is not self and self.is_alive():
            self.join()
        log_system(f"[Speaker: {self.mac_address}] Thread stopped")

    def _connect(self):
        """
        Attempts to connect to the Bluetooth speaker.
        """
        try:
            result = subprocess.run(
                ["bluetoothctl", "connect", self.mac_address],
                capture_output=True, text=True, timeout=10
            )
            if "Connection successful" in result.stdout:
                self.connected = True
                log_system(f"[Speaker: {self.mac_address}] Connected successfully")
                self._connection_feedback()
            else:
                log_system(f"[Speaker: {self.mac_address}] Connection failed: {result.stdout}", level="WARNING")
                self.connected = False
        except Exception as e:
            log_system(f"[Speaker: {self.mac_address}] Exception during connection: {e}", level="ERROR")
            self.connected = False

    def _disconnect(self):
        """
        Disconnects from the Bluetooth speaker.
        """
        try:
            subprocess.run(
                ["bluetoothctl", "disconnect", self.mac_address],
                capture_output=True, text=True
            )
            self.connected = False
            self._disconnection_feedback()
        except Exception as e:
            log_system(f"[Speaker: {self.mac_address}] Exception during disconnection: {e}", level="ERROR")

    def _is_connected(self) -> bool:
        """
        Checks whether the speaker is currently connected.
        :return: True if connected, False otherwise
        """
        try:
            result = subprocess.run(
                ["bluetoothctl", "info", self.mac_address],
                capture_output=True, text=True
            )
            out = (result.stdout or "").lower() # case-insensitive
            return "connected: yes" in out
        except Exception as e:
            log_system(f"[Speaker: {self.mac_address}] Error checking status: {e}", level="ERROR")
            return False

    def _reconnection_attempts(self):
        """
        Attempts to reconnect to the speaker using fast and slow retry strategies.
        """
        log_system(f"[Speaker: {self.mac_address}] Starting reconnection procedure.")

        # Fast retry attempts
        for attempt in range(self.fast_retry_attempts):
            if self.stop_event.is_set():
                return
            if self.stop_event.wait(self.retry_interval):
                return
            self._connect()
            if self.connected:
                log_system(f"[Speaker: {self.mac_address}] Reconnected successfully.")
                return
            else:
                log_system(f"[Speaker: {self.mac_address}] Retry {attempt + 1}/{self.fast_retry_attempts} failed", level="WARNING")


        # Slow retry loop
        log_system(f"[Speaker: {self.mac_address}] All fast retries failed. Retrying every {self.retry_sleep}s.")
        while not self.stop_event.is_set():
            if self.stop_event.wait(self.retry_sleep):
                return
            self._connect()
            if self.connected:
                log_system(f"[Speaker: {self.mac_address}] Reconnected successfully.")
                return
            log_system(f"[Speaker: {self.mac_address}] Slow retry failed", level="WARNING")

    def _connection_feedback(self):
        """
        Plays a voice line to confirm connection to the device.
        """
        self.execute(file=AudioLibrary.SPEAKER_CONNECT)

    def _disconnection_feedback(self):
        """
        Write on the system log to confirm disconnection to the device.
        """
        # Can't reproduce audio if already disconnected
        log_system(f"[Speaker: {self.mac_address}] Disconnected", level="INFO")
