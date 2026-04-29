# speaker.py
# Actuator module for Bluetooth speaker control and audio playback.
#
# Author:
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

import asyncio
import threading
import time
from pathlib import Path
from typing import Optional

from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType
from dbus_fast.errors import DBusError
from dbus_fast.signature import Variant
from playsound import playsound

from utils.logger import log_system
from utils.config import get_speaker_config
from utils.audio_paths import AudioLibrary
from utils.lock import device_reconnection_lock


class _BlueZSpeakerClient:
    """
    Private helper around BlueZ D-Bus APIs using dbus-fast.
    Keeps all Bluetooth management inside speaker.py without subprocess.
    """

    BLUEZ_SERVICE = "org.bluez"
    OBJ_MANAGER_PATH = "/"
    OBJ_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
    PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
    ADAPTER_IFACE = "org.bluez.Adapter1"
    DEVICE_IFACE = "org.bluez.Device1"

    def __init__(self):
        self.bus = None
        self.adapter_path = None
        self.object_manager = None
        self._device_path_cache = {}

    @staticmethod
    def _unwrap(value):
        """
        Unwraps dbus-fast Variant values into plain Python values.
        """
        return value.value if isinstance(value, Variant) else value

    async def connect(self):
        """
        Connects to the system bus and resolves the default Bluetooth adapter.
        """
        if self.bus is not None:
            return

        self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        introspection = await self.bus.introspect(
            self.BLUEZ_SERVICE,
            self.OBJ_MANAGER_PATH
        )
        obj = self.bus.get_proxy_object(
            self.BLUEZ_SERVICE,
            self.OBJ_MANAGER_PATH,
            introspection
        )
        self.object_manager = obj.get_interface(self.OBJ_MANAGER_IFACE)

        managed = await self.object_manager.call_get_managed_objects()

        for path, interfaces in managed.items():
            if self.ADAPTER_IFACE in interfaces:
                self.adapter_path = path
                break

        if not self.adapter_path:
            raise RuntimeError("No BlueZ adapter found")

    async def close(self):
        """
        Closes the D-Bus connection if open.
        """
        if self.bus is not None:
            try:
                self.bus.disconnect()
            except Exception:
                pass
            finally:
                self.bus = None
                self.adapter_path = None
                self.object_manager = None
                self._device_path_cache.clear()

    async def _get_managed_objects(self):
        """
        Returns all BlueZ managed objects.
        """
        await self.connect()
        return await self.object_manager.call_get_managed_objects()

    async def _get_adapter_interfaces(self):
        """
        Returns adapter and properties interfaces for the active adapter.
        """
        await self.connect()

        introspection = await self.bus.introspect(
            self.BLUEZ_SERVICE,
            self.adapter_path
        )
        obj = self.bus.get_proxy_object(
            self.BLUEZ_SERVICE,
            self.adapter_path,
            introspection
        )
        adapter = obj.get_interface(self.ADAPTER_IFACE)
        props = obj.get_interface(self.PROPERTIES_IFACE)
        return adapter, props

    async def _get_device_interfaces(self, device_path: str):
        """
        Returns device and properties interfaces for a BlueZ device path.
        """
        await self.connect()

        introspection = await self.bus.introspect(
            self.BLUEZ_SERVICE,
            device_path
        )
        obj = self.bus.get_proxy_object(
            self.BLUEZ_SERVICE,
            device_path,
            introspection
        )
        device = obj.get_interface(self.DEVICE_IFACE)
        props = obj.get_interface(self.PROPERTIES_IFACE)
        return device, props

    async def _resolve_device_path(self, mac_address: str) -> Optional[str]:
        """
        Resolves a MAC address to a BlueZ device object path.
        """
        mac_upper = mac_address.upper()

        if mac_upper in self._device_path_cache:
            return self._device_path_cache[mac_upper]

        managed = await self._get_managed_objects()

        for path, interfaces in managed.items():
            dev = interfaces.get(self.DEVICE_IFACE)
            if not dev:
                continue

            address = self._unwrap(dev.get("Address"))
            if address and str(address).upper() == mac_upper:
                self._device_path_cache[mac_upper] = path
                return path

        return None

    async def _set_trusted(self, device_path: str, value: bool = True):
        """
        Sets the Trusted property on a device.
        """
        _, props = await self._get_device_interfaces(device_path)
        await props.call_set(self.DEVICE_IFACE, "Trusted", Variant("b", value))

    async def scan_devices(self, timeout: int) -> list[str]:
        """
        Scans for nearby Bluetooth devices and returns likely audio device MACs.

        Current strategy is intentionally relaxed:
        - if audio-related UUID/icon exists -> include
        - if paired and named -> include
        - duplicates are removed
        """
        cfg = get_speaker_config() or {}
        timeout = int(cfg.get("scan_timeout", 5)) if timeout is None else int(timeout)

        await self.connect()
        adapter, _ = await self._get_adapter_interfaces()

        log_system(f"[Speaker Scanner] Starting Bluetooth scan for {timeout} seconds...")

        try:
            await adapter.call_start_discovery()
        except DBusError as e:
            if "InProgress" not in str(e):
                raise

        try:
            await asyncio.sleep(timeout)
        finally:
            try:
                await adapter.call_stop_discovery()
            except Exception:
                pass

        managed = await self._get_managed_objects()
        mac_list = []

        for path, interfaces in managed.items():
            dev = interfaces.get(self.DEVICE_IFACE)
            if not dev:
                continue

            mac = self._unwrap(dev.get("Address"))
            name = self._unwrap(dev.get("Name")) or self._unwrap(dev.get("Alias")) or ""
            icon = self._unwrap(dev.get("Icon")) or ""
            uuids = self._unwrap(dev.get("UUIDs")) or []
            paired = bool(self._unwrap(dev.get("Paired")) or False)

            name = str(name).strip()
            icon = str(icon).lower()
            uuids = [str(u).lower() for u in uuids]

            looks_audio = (
                "audio" in icon
                or "sink" in icon
                or any("110b" in u or "110d" in u or "110e" in u or "111e" in u for u in uuids)
            )

            # Relaxed filter:
            # - audio-looking devices
            # - or paired devices with a usable name
            if mac and (looks_audio or (paired and name)):
                log_system(f"[Speaker Scanner] Audio device found: {mac}")
                mac_list.append(str(mac).upper())

        mac_list = list(dict.fromkeys(mac_list))

        if not mac_list:
            log_system("[Speaker Scanner] No compatible speakers found.", level="WARNING")

        return mac_list

    async def is_connected(self, mac_address: str) -> bool:
        """
        Returns True if the device is currently connected.
        """
        device_path = await self._resolve_device_path(mac_address)
        if not device_path:
            return False

        _, props = await self._get_device_interfaces(device_path)
        value = await props.call_get(self.DEVICE_IFACE, "Connected")
        return bool(self._unwrap(value))

    async def connect_device(self, mac_address: str) -> bool:
        """
        Connects to a device by MAC address.
        """
        device_path = await self._resolve_device_path(mac_address)
        if not device_path:
            raise RuntimeError(f"BlueZ device path not found for {mac_address}")

        device, _ = await self._get_device_interfaces(device_path)

        try:
            await self._set_trusted(device_path, True)
        except Exception:
            pass

        await device.call_connect()
        return await self.is_connected(mac_address)

    async def disconnect_device(self, mac_address: str) -> bool:
        """
        Disconnects a device by MAC address.
        Returns True if it ends up disconnected.
        """
        device_path = await self._resolve_device_path(mac_address)
        if not device_path:
            return True

        device, _ = await self._get_device_interfaces(device_path)

        try:
            await device.call_disconnect()
        except DBusError:
            pass

        return not await self.is_connected(mac_address)


def scan_speaker_devices(timeout: int) -> list[str]:
    """
    Scans for nearby Bluetooth speakers using BlueZ over D-Bus
    and returns a list of MAC addresses.
    """
    async def _runner():
        client = _BlueZSpeakerClient()
        try:
            return await client.scan_devices(timeout)
        finally:
            await client.close()

    try:
        return asyncio.run(_runner())
    except Exception as e:
        log_system(f"[Speaker Scanner] Scan error: {e}", level="ERROR")
        return []


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
        self.mac_address = mac_address.upper()
        self.event = threading.Event()
        self.stop_event = threading.Event()
        self.file = None
        self.connected = False

        self.client = _BlueZSpeakerClient()
        self.loop = None

        cfg = get_speaker_config() or {}
        self.fast_retry_attempts = int(cfg.get("fast_retry_attempts", 5))
        self.retry_interval = int(cfg.get("retry_interval", 5))
        self.retry_sleep = int(cfg.get("retry_sleep", 60))

    def _run_async(self, coro):
        """
        Runs a coroutine on the thread-owned event loop.
        Must only be called from this thread after loop initialization.
        """
        if self.loop is None:
            raise RuntimeError("Speaker event loop is not initialized")
        return self.loop.run_until_complete(coro)

    def run(self):
        """
        Main loop that ensures connection is maintained and audio playback
        is triggered when requested.
        """
        log_system(f"[Speaker: {self.mac_address}] Thread started")

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            while not self.stop_event.is_set():
                is_conn = self._is_connected_internal()
                self.connected = is_conn

                if not is_conn:
                    with device_reconnection_lock:
                        self._reconnection_attempts()
                    self.connected = self._is_connected_internal()

                if self.event.is_set():
                    try:
                        if self.connected and self.file:
                            p = Path(self.file)
                            if p.exists():
                                if not self.stop_event.is_set() and self._is_connected_internal():
                                    log_system(f"[Speaker: {self.mac_address}] Playing audio: {p}")
                                    playsound(str(p))
                                else:
                                    log_system(
                                        f"[Speaker: {self.mac_address}] Skipping playback (stopping or disconnected)",
                                        level="WARNING"
                                    )
                            else:
                                log_system(
                                    f"[Speaker: {self.mac_address}] File not found or invalid: {self.file}",
                                    level="WARNING"
                                )
                        elif not self.file:
                            log_system(f"[Speaker: {self.mac_address}] No audio file provided", level="WARNING")
                    except Exception as e:
                        log_system(f"[Speaker: {self.mac_address}] Error during audio playback: {e}", level="ERROR")
                    finally:
                        self.event.clear()

                time.sleep(1)
        finally:
            try:
                self._disconnect_internal()
            except Exception:
                pass

            try:
                self._run_async(self.client.close())
            except Exception:
                pass

            try:
                self.loop.close()
            except Exception:
                pass

            self.loop = None
            self.connected = False

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

    def is_connected(self) -> bool:
        """
        Public state accessor. Safe to call from other threads.
        """
        return bool(self.connected)

    def _connect_internal(self):
        """
        Attempts to connect to the Bluetooth speaker through BlueZ D-Bus.
        Must only be called from the speaker thread.
        """
        try:
            was_connected = self._is_connected_internal()
            ok = self._run_async(self.client.connect_device(self.mac_address))
            self.connected = bool(ok)

            if self.connected:
                log_system(f"[Speaker: {self.mac_address}] Connected successfully")
                if not was_connected:
                    self._connection_feedback()
            else:
                log_system(f"[Speaker: {self.mac_address}] Connection failed", level="WARNING")
        except Exception as e:
            log_system(f"[Speaker: {self.mac_address}] Exception during connection: {e}", level="ERROR")
            self.connected = False

    def _disconnect_internal(self):
        """
        Disconnects from the Bluetooth speaker through BlueZ D-Bus.
        Must only be called from the speaker thread.
        """
        try:
            was_connected = self._is_connected_internal()
            self._run_async(self.client.disconnect_device(self.mac_address))
            self.connected = False

            if was_connected:
                self._disconnection_feedback()
        except Exception as e:
            log_system(f"[Speaker: {self.mac_address}] Exception during disconnection: {e}", level="ERROR")

    def _is_connected_internal(self) -> bool:
        """
        Checks whether the speaker is currently connected.
        Must only be called from the speaker thread.
        """
        try:
            return bool(self._run_async(self.client.is_connected(self.mac_address)))
        except Exception as e:
            log_system(f"[Speaker: {self.mac_address}] Error checking status: {e}", level="ERROR")
            return False

    def _reconnection_attempts(self):
        """
        Attempts to reconnect to the speaker using fast and slow retry strategies.
        Must only be called from the speaker thread.
        """
        log_system(f"[Speaker: {self.mac_address}] Starting reconnection procedure.")

        for attempt in range(self.fast_retry_attempts):
            if self.stop_event.is_set():
                return
            if self.stop_event.wait(self.retry_interval):
                return

            self._connect_internal()
            if self.connected:
                log_system(f"[Speaker: {self.mac_address}] Reconnected successfully.")
                return

            log_system(
                f"[Speaker: {self.mac_address}] Retry {attempt + 1}/{self.fast_retry_attempts} failed",
                level="WARNING"
            )

        log_system(
            f"[Speaker: {self.mac_address}] All fast retries failed. Retrying every {self.retry_sleep}s."
        )

        while not self.stop_event.is_set():
            if self.stop_event.wait(self.retry_sleep):
                return

            self._connect_internal()
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
        log_system(f"[Speaker: {self.mac_address}] Disconnected", level="INFO")