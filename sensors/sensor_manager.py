# sensor_manager.py
# Manager for initializing and coordinating BlueCoin sensors threads
#
# Author: Francesco Urru
# Github: https://github.com/frarvo
# Repository: https://github.com/frarvo/CPSA_2026
# License: MIT

from blue_st_sdk.features.feature_accelerometer import FeatureAccelerometer
from blue_st_sdk.features.feature_gyroscope import FeatureGyroscope
from sensors.BLE.feature_mems_sensor_fusion_compact import FeatureMemsSensorFusionCompact

from sensors.BLE.bluecoin import scan_bluecoin_devices, BlueCoinThread
from sensors.BLE.feature_listeners import AccelerometerFeatureListener, GyroscopeFeatureListener, QuaternionFeatureListener

from sensors.USB.camera_yolo import YoloDpuThread

from IMU_pipeline.data_stream.synchronizer import IMUSynchronizer
from IMU_pipeline.classifiers.stereotipy_classifier.stereotipy_classifier import StereotipyClassifier

from utils.config import get_bluecoin_config
from utils.logger import log_system
from utils.lock import device_scan_lock, device_connection_lock


class SensorManager:
    """
    Manages initialization and coordination of BlueCoin sensor threads.

    This manager:
    - Loads configuration from config.yaml
    - Scans for available BlueCoin bluecoins (scan_sensors)
    - Initializes and starts sensor threads with three features per device
    - Feed samples to a shared synchronizer (sync left and right data streams)
    """

    def __init__(self):
        """Initializes the SensorManager and loads BlueCoin configuration."""
        self.threads = []
        self.config = get_bluecoin_config()
        self.bluecoins = []
        self.synchronizer = IMUSynchronizer()
        self.classifier = StereotipyClassifier()
        self.synchronizer.buffer.set_features_sink(self.classifier.recognize)
        log_system("[SensorManager] Initialized")
        self.yolo_thread = YoloDpuThread()

    def scan_sensors(self):
        """Performs BLE scan for BlueCoin devices and stores results internally."""
        log_system("[SensorManager] Starting BLE scan for BlueCoin devices")
        with device_scan_lock:
            self.bluecoins = scan_bluecoin_devices(timeout=5)
        log_system(f"[SensorManager] Found {len(self.bluecoins)} BlueCoin device(s)")

        discovered = []
        for node in self.bluecoins:
            try:
                discovered.append(node.get_name())
            except Exception as e:
                log_system(f"[SensorManager] Error retrieving name for scanned node: {e}", level="WARNING")

    def initialize_sensors(self):
        """
        Initializes sensor threads for bluecoins, Faros and breath sensors.
        """
        if not self.bluecoins:
            log_system("[SensorManager] No scanned bluecoins available. Run scan_sensors() first.", level="WARNING")
            return
        # Local name->node map
        by_name = {}
        for node in self.bluecoins:
            try:
                name = node.get_name()
                if name:
                    by_name[name] = node
            except Exception as e:
                log_system(f"[SensorManager] Can't read node name: {e}", level="WARNING")

        # Expected 2 bluecoins bc_left and bc_right
        expected = {c.get("id"): c.get("name") for c in self.config if c.get("id") and c.get("name")}
        left_name = expected.get("bc_left")
        right_name = expected.get("bc_right")

        if not left_name or not right_name:
            log_system(f"[SensorManager] Config must include bc_left and bc_right with names.", level="ERROR")
            return

        # Check node presence
        missing = [name for name in (left_name, right_name) if name not in by_name]
        if missing:
            log_system(f"[SensorManager] Missing expected bluecoins: {missing}", level="ERROR")
            return

        # Initialize sensors

        for sensor_id, expected_name in (("bc_left", left_name), ("bc_right", right_name)):
            node = by_name[expected_name]

            # Attempt to retrieve feature from node
            try:
                feat_acc = node.get_feature(FeatureAccelerometer)
                feat_gyr = node.get_feature(FeatureGyroscope)
                feat_quat = node.get_feature(FeatureMemsSensorFusionCompact)
            except Exception as e:
                log_system(f"[SensorManager] Error retrieving features for '{expected_name}': {e}", level="ERROR")
                continue

            features, listeners = [], []
            if feat_acc:
                features.append(feat_acc)
                listeners.append(AccelerometerFeatureListener(device_id=sensor_id, synchronizer=self.synchronizer))
            else:
                log_system(f"[SensorManager] {expected_name} is missing Accelerometer", level="WARNING")

            if feat_gyr:
                features.append(feat_gyr)
                listeners.append(GyroscopeFeatureListener(device_id=sensor_id, synchronizer=self.synchronizer))
            else:
                log_system(f"[SensorManager] {expected_name} is missing Gyroscope", level="WARNING")

            if feat_quat:
                features.append(feat_quat)
                listeners.append(QuaternionFeatureListener(device_id=sensor_id, synchronizer=self.synchronizer))
            else:
                log_system(f"[SensorManager] {expected_name} is missing Quaternions", level="WARNING")


            if not features:
                log_system(f"[SensorManager] No features available on node {expected_name}", level="WARNING")
                continue

            # Initialize and start the thread
            try:
                with device_connection_lock:
                    thread = BlueCoinThread(
                        node=node,
                        feature=features,
                        feature_listener=listeners,
                        device_id=sensor_id
                    )
                    thread.start()
                    self.threads.append(thread)
                log_system(f"[SensorManager] Sensor initialized: {sensor_id} ({expected_name}) with {len(features)} features")
            except Exception as e:
                log_system(f"[SensorManager] Error initializing thread for '{sensor_id}'/'{expected_name}': {e}", level="ERROR")

        try:
            self.yolo_thread.start()
            log_system("[SensorManager] YOLO camera thread initialized")
        except Exception as e:
            log_system(f"[SensorManager] YOLO camera thread initialization failed: {e}", level="ERROR")

        log_system("[SensorManager] All sensor threads initialized")

    def stop_all(self):
        """Stops all active sensor threads and clears the list."""
        log_system("[SensorManager] Stopping all sensor threads...")
        for thread in self.threads:
            try:
                thread.stop()
            except Exception as e:
                log_system(f"[SensorManager] Error stopping thread for device '{thread.device_id}': {e}", level="ERROR")
        self.threads.clear()

        try:
            self.yolo_thread.stop()
        except Exception as e:
            log_system(f"[SensorManager] Error stopping YOLO camera thread: {e}", level="ERROR")

        log_system("[SensorManager] All sensor threads stopped.")

    def get_sensors_names(self):
        """
        Returns the names of the discovered BlueCoin bluecoins
        """
        try:
            return [n.get_name() for n in self.bluecoins if n.get_name()]
        except Exception:
            return []

    def get_yolo_thread(self):
        return self.yolo_thread
