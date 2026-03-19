# bluecoin.py
# BLE interface module for BlueCoin sensor devices (STMicroelectronics)
#
# Author: Francesco Urru
# Github: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

import time
import threading
from typing import Sequence, List

from blue_st_sdk.manager import Manager, ManagerListener
from blue_st_sdk.node import NodeStatus, NodeListener
from bluepy.btle import BTLEDisconnectError

from utils.logger import log_system
from utils.lock import device_reconnection_lock


class BlueCoinManagerListener(ManagerListener):
    """ Custom listener for BlueCoin discovery. Logs events during BLE scan. """
    def on_discovery_change(self, manager, enabled):
        log_system(f"[BlueCoin Scanner] Discovery {'started' if enabled else 'stopped'}.")


    def on_node_discovered(self, manager, node):
        try:
            log_system(f"[BlueCoin Scanner] Found node: {node.get_name()} - {node.get_tag()}")
        except Exception:
            log_system(f"[BlueCoin Scanner] Found node: (name/tag unavailable)")


class BlueCoinNodeListener(NodeListener):
    """ Custom listener for BlueCoin Nodes. Logs events during BLE connections and disconnections. """
    def on_connect(self, node):
        log_system(f"[BlueCoin node] {node.get_name()}: {node.get_tag()} connected")

    def on_disconnect(self, node, unexpected=False):
        log_system(f"[BlueCoin node] {node.get_name()}: {node.get_tag()} disconnected {'unexpectedly' if unexpected else ' '}")

    def on_status_change(self, node, new_status, old_status):
        log_system(f"[BlueCoin node] Status changed from {old_status} to {new_status}")


def scan_bluecoin_devices(timeout: int = 5) -> list:
    """
    Performs a BLE scan to discover nearby BlueCoin nodes.
    :param timeout: Duration in seconds for the scan.
    :return: List of compatible BlueCoin nodes discovered during the scan.
    """
    nodes = []

    log_system(f"[BlueCoin Scanner] Starting BLE scan for {timeout} seconds...")
    manager = Manager.instance()
    listener = BlueCoinManagerListener()
    manager.add_listener(listener)

    try:
        manager.discover(timeout)
        nodes = manager.get_nodes()
    except Exception as e:
        log_system(f"[BlueCoin Scanner] Error during discovery: {e}", level="ERROR")
    finally:
        try:
            manager.remove_listener(listener)
        except Exception:
            pass

    if not nodes:
        log_system("[BlueCoin Scanner] No BlueCoin devices found.", level="WARNING")
    else:
        log_system(f"[BlueCoin Scanner] Total devices found: {len(nodes)}")

    return nodes

class BlueCoinThread(threading.Thread):
    """
    Thread for managing connection to a single BlueCoin device with multiple features at the same time.
    Features can be pass either as single instance or list.
    Parameters:
        node: BlueST Node object representing the BlueCoin device.
        feature: Feature or list[Feature].
        feature_listener: FeatureListener or list[FeatureListener]. Same length as feature.
        device_id: Identifier string for the device.
    """

    def __init__(self, node, feature, feature_listener, device_id:str):
        super().__init__(daemon=True)
        self.node = node
        self.node_listener = BlueCoinNodeListener()
        self.device_id = device_id
        self.stop_event = threading.Event()

        # Distinguish between single istance or list
        if isinstance(feature, (list,tuple)):
            self.features: List = list(feature)
        else:
            self.features: List = [feature]

        if isinstance(feature_listener, (list,tuple)):
            self.feature_listeners: List = list(feature_listener)
        else:
            self.feature_listeners: List = [feature_listener]

        # Check length correspondence
        if len(self.features) != len(self.feature_listeners):
            raise ValueError("features and feature_listeners must have the same length")


    # Thread lifecycle
    def run(self):
        log_system(f"[BlueCoin Thread: {self.device_id}] Thread started.")
        ok = self._connect()
        if not ok or self.stop_event.is_set():
            self._cleanup()
            return
        self._start_notifications()
        self._listen()

    def stop(self):
        self.stop_event.set()
        if self.is_alive():
            self.join()
        log_system(f"[BlueCoin Thread: {self.device_id}] Thread stopped.")

    # Thread internals
    def _connect(self) -> bool:
        self.node.add_listener(self.node_listener)
        while not self.node.connect():
            if self.stop_event.is_set():
                return False
            log_system(f"[BlueCoin Thread: {self.device_id}] Connection failed, retrying...", level="WARNING")
            # 1 second interruptable wait
            for _ in range(10):
                if self.stop_event.is_set():
                    return False
                time.sleep(0.1)
        log_system(f"[BlueCoin Thread: {self.device_id}] Connected successfully.")
        # Attach listeners for all features
        for feature, listener in zip(self.features, self.feature_listeners):
            try:
                feature.add_listener(listener)
            except Exception as e:
                log_system(f"[BlueCoin Thread: {self.device_id}] add_listener error: {e}", level="ERROR")
        return True

    def _start_notifications(self):
        # Enable BLE notifications for all features
        for feature in self.features:
            try:
                self.node.enable_notifications(feature)
            except Exception as e:
                log_system(f"[BlueCoin Thread: {self.device_id}] enable_notifications error: {e}", level="ERROR")

    def _stop_notifications(self):
        # Disable BLE notifications and remove listeners for all features
        for feature, listener in zip(self.features, self.feature_listeners):
            try:
                self.node.disable_notifications(feature)
            except Exception:
                pass
            try:
                feature.remove_listener(listener)
            except Exception:
                pass

    def _listen(self):
        while not self.stop_event.is_set():
            try:
                if self.node.get_status() != NodeStatus.CONNECTED:
                    self._handle_reconnection()
                else:
                    self.node.wait_for_notifications(0.05)
            except BTLEDisconnectError:
                log_system(f"[BlueCoin Thread: {self.device_id}] BTLE exception caught", level="ERROR")
                self._handle_reconnection()
            except Exception as e:
                log_system(f"[BlueCoin Thread: {self.device_id}] wait_for_notifications error: {e}", level="ERROR")
                self._handle_reconnection()
        self._cleanup()

    def _handle_reconnection(self):
        self._stop_notifications()
        with device_reconnection_lock:
            while not self.stop_event.is_set():
                try:
                    log_system(f"[BlueCoin Thread: {self.device_id}] Attempting reconnection...")
                    if self.node.connect():
                        log_system(f"[BlueCoin Thread: {self.device_id}] Reconnected successfully.")
                        # Reattach listeners and re-enable notifications on reconnection
                        for feature, listener in zip(self.features, self.feature_listeners):
                            try:
                                feature.add_listener(listener)
                            except Exception:
                                pass
                        self._start_notifications()
                        return
                except BTLEDisconnectError:
                    log_system(f"[BlueCoin Thread: {self.device_id}] Reconnection failed, retrying...", level="WARNING")
                except Exception as e:
                    log_system(f"[BlueCoin Thread: {self.device_id}] Reconnection error: {e}", level="ERROR")
                # 2 seconds interruptable wait
                for _ in range(20):
                    if self.stop_event.is_set():
                        return
                    time.sleep(0.1)



    def _cleanup(self):
        try:
            self._stop_notifications()
        except Exception:
            # Doesn't raise exception during shutdown
            pass
        # Remove listener before disconnect
        try:
            self.node.remove_listener(self.node_listener)
        except Exception:
            # Doesn't raise exception during shutdown
            pass
        try:
            if self.node.get_status() == NodeStatus.CONNECTED:
                self.node.disconnect()
                log_system(f"[BlueCoin Thread: {self.device_id}] Disconnected cleanly.")
        except Exception:
            # Doesn't raise exception during shutdown
            pass