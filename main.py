# main.py
# Entry point for the CPSA_2026 system
# Receives IMU+Quaternion data from dual wrist bracelets (BlueCoin), detect stereotipy events, logs them and calls actuation accordingly.
# Sensor manage scans for sensors, connect to sensors, sends data to synchronizer,
# Synchronizer syncs the two data streams and fills a buffer.
# Buffer fill up and call processing.
# Processing extracts features from IMU data and arm angle from quaternions, when ready calls classifier.
# Classifier generates stereotipy event and pushes events to queue.
# Dispatcher consumes event queue, logs to event diary and calls actuation based on actuation policy.
# Actuation policy decides which actuator to use and for how long. Has memory for most effectiveness.
#
# Author: Francesco Urru
# Repository: https://github.com/frarvo/CPSA_2026
# License: MIT


import time

from sensors.sensor_manager import SensorManager
from actuators.actuator_manager import ActuatorManager

from sensors.USB.yolo_DPU import YoloDpuThread

from core.actuation_policy import StereotipyActivationPolicy
from core.event_dispatcher import EventDispatcher


from utils.logger import log_system
from utils.config import get_bluecoin_config


def main():
    log_system("[MAIN] Initializing STOPme system...")

    # Initialize managers
    sensor_manager = SensorManager()
    actuator_manager = ActuatorManager()

    # Scan sensors
    sensor_manager.scan_sensors()

    # Repeats scan to ensure that required BlueCoin sensors are present
    expected_names = {entry.get("name") for entry in get_bluecoin_config() if entry.get("name")}
    if expected_names:
        max_sensor_retries = 5
        retry_delay_sec = 5
        attempt = 0
        def actual_sensors():
            return set(sensor_manager.get_sensors_names())

        while not expected_names.issubset(actual_sensors()) and attempt < max_sensor_retries:
            missing = expected_names - actual_sensors()
            log_system(f"[MAIN] Waiting for BlueCoin sensors: missing = {missing}. "
                       f"Retrying in {retry_delay_sec}s "
                       f"({attempt+1}/{max_sensor_retries})",
                       level="WARNING"
                       )
            time.sleep(retry_delay_sec)
            sensor_manager.scan_sensors()
            attempt += 1
        if not expected_names.issubset(actual_sensors()):
            log_system(f"[MAIN] Required BlueCoin sensors not found. Aborting startup.", level="ERROR")
            return

    # Scan actuators
    actuator_manager.scan_actuators()

    # Initialize sensors and actuators
    actuator_manager.initialize_actuators()
    sensor_manager.initialize_sensors()

    # Extract actuator lists
    actuators_list = actuator_manager.get_actuators_ids()
    if not actuators_list:
        log_system("[MAIN] No actuators discovered. Event detection and logging still executing")

    # Instantiate activation policy
    policy = StereotipyActivationPolicy(actuator_ids=actuators_list)

    yolo_thread = YoloDpuThread()

    # Instantiate event dispatcher
    dispatcher = EventDispatcher(
        actuator_manager=actuator_manager,
        policy=policy,
        yolo_thread=yolo_thread
    )


    # Initialize event dispatcher
    try:
        dispatcher.start()
        yolo_thread.start()
    except Exception as e:
        log_system(f"[MAIN] Failed to start runtime threads: {e}", level="ERROR")
        dispatcher.stop()
        yolo_thread.stop()
        sensor_manager.stop_all()
        actuator_manager.stop_all()
        return


    log_system("[MAIN] System is now running. Press Ctrl+C to terminate.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_system("[MAIN] Termination signal received.")
    except Exception as e:
        log_system(f"[MAIN] Unhandled error in main loop: {e}", level="ERROR")
    finally:
        dispatcher.stop()
        yolo_thread.stop()
        sensor_manager.stop_all()
        actuator_manager.stop_all()
        log_system("[MAIN] System shutdown complete.")


if __name__ == "__main__":
    main()