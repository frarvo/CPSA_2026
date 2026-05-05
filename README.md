# CPSA_2026

Modular Python Cyber-Physical System for real-time multisensory feedback.

CPSA_2026 is a modular and extensible Cyber-Physical System designed to connect wearable BLE sensors, parallel sensing pipelines, and multisensory actuators to provide adaptive real-time feedback based on detected events.

The project evolves from the STOPme prototype, extending the original IMU-based architecture with additional processing pipelines, vision-based detection, hardware-accelerated inference, and a fully event-driven modular design.

The system combines:

* BLE wearable sensing
* synchronized multi-stream processing
* C-based feature extraction pipelines
* embedded classifiers
* DPU-accelerated computer vision
* event-driven coordination
* multimodal actuation

The architecture is designed to remain modular and extensible.

---

# Features

* Real-time BLE IMU acquisition
* Parallel multi-pipeline architecture
* Dual-wrist synchronization with configurable timing tolerance
* Sliding window buffering with overlap
* Quaternion-based preprocessing pipeline
* C-accelerated feature extraction
* Embedded classifier integration through shared libraries
* Vision pipeline using Xilinx DPU acceleration
* Event-driven architecture with bounded queues
* Modular actuator abstraction layer
* Multi-modal feedback:

  * Wi-Fi LED strip
  * BLE MetaMotion haptic feedback
  * Bluetooth audio feedback
* Adaptive actuation policy with retry and fallback logic
* Automatic reconnection handling
* Thread-safe logging and event tracking
* Modular and extensible architecture

---
# README Structure

This README is organized as both a setup guide and a technical overview of the CPSA_2026 system.

The first sections describe the general purpose of the project, its main features, the system architecture, and the current repository structure.

The setup sections cover the required operating system, Python dependencies, DPU/Vitis-AI configuration, Bluetooth setup for the Kria KV260, and BlueST SDK notes.

The architecture sections explain how the IMU pipeline, VIDEO pipeline, event queue, dispatcher, actuation policy, and actuator layer work together at runtime.

The usage section explains how to run the main system entry point and how `main.py` initializes and controls the full runtime.

The extension sections describe how to add new sensors, add new actuators, and modify the actuation policy.

## Table of Contents

- [Features](#features)
- [System Overview](#system-overview)
- [Requirements](#requirements)
- [System Dependencies](#system-dependencies)
- [Python Dependencies](#python-dependencies)
- [Project Structure](#project-structure)
- [IMU Pipeline](#imu-pipeline)
- [VIDEO Pipeline](#video-pipeline)
- [DPU / Vitis-AI Setup](#dpu--vitis-ai-setup)
- [Bluetooth Setup (Kria KV260)](#bluetooth-setup-kria-kv260)
- [BlueST SDK Setup](#bluest-sdk-setup)
- [Adding Custom BlueCoin Features](#adding-custom-bluecoin-features)
- [How It Works](#how-it-works)
- [Event System](#event-system)
- [Event Dispatcher](#event-dispatcher)
- [Actuation Policy](#actuation-policy)
- [Runtime Lifecycle](#runtime-lifecycle)
- [Logging](#logging)
- [Configuration](#configuration)
- [Usage](#usage)
- [Adding New Sensors](#adding-new-sensors)
- [Adding New Actuators](#adding-new-actuators)
- [Modifying the Actuation Policy](#modifying-the-actuation-policy)
- [Author](#author)
---

# System Overview

```text
Sensor Pipelines / External Inputs
        │
        ├── IMU Pipeline (BlueCoin)
        ├── Vision Pipeline (YOLO DPU)
        ├── Additional Parallel Pipelines
        │
        ▼
Shared Event System
        ▼
Event Dispatcher
        ▼
Actuation Policy Engine
        ▼
Multimodal Actuators
```

---

# Requirements

## Operating System

Tested on:

* Ubuntu 22.04
* Kernel: 5.15.0-1067-xilinx-zynqmp

Notes:

* Newer Ubuntu versions may introduce BLE stack incompatibilities.
* The VIDEO pipeline was tested on Xilinx Kria KV260.

---

## Python Version

Tested on:

* Python 3.10

---

## pip Version

* pip 22.0.2

---

# System Dependencies

```bash
sudo apt update
sudo apt upgrade

sudo apt install python3-pip python3-distutils libglib2.0-dev

sudo apt install -y build-essential tk-dev libncurses5-dev libncursesw5-dev \
libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev \
libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev \
bluetooth bluez libbluetooth-dev libudev-dev libboost-all-dev git

sudo apt install libcap2-bin
```

---

# Python Dependencies

```bash
pip install \
numpy \
pyyaml \
playsound \
flux_led \
opuslib \
bluepy \
blue-st-sdk \
metawear \
```

---

# Project Structure

```bash
CPSA_2026/
├── actuators/
│   ├── actuator_manager.py
│   ├── BLE/
│   │   └── metamotion.py
│   ├── BT/
│   │   └── speaker.py
│   └── WIFI/
│       └── led_strip.py
│
├── assets/
│   └── audio/
│       └── *.mp3 (Audio files)
│
├── core/
│   ├── actuation_policy.py
│   └── event_dispatcher.py
│
├── IMU_pipeline/
│   ├── classifiers/
│   │   └── stereotipy_classifier/
│   │       ├── libPredictPericolosaWristsQuat.so
│   │       ├── predict_models_wrapper_quat.py
│   │       ├── Predict_Pericolosa_Wrists_Quat/
│   │       │   └── * source files for libPredictPericolosaWristsQuat.so binary build
│   │       └── stereotipy_classifier.py
│   │
│   └── data_stream/
│       ├── data_buffer.py
│       ├── data_processing_wrapper_quat.py
│       ├── libProcessDataWristsQuat.so
│       ├── ProcessDataWristsQuat/
│       │   └── * source files for libProcessDataWristsQuat.so binary build
│       └── synchronizer.py
│
├── sensors/
│   ├── BLE/
│   └── sensor_manager.py
│
├── utils/
│   ├── audio_paths.py
│   ├── config.py
│   ├── event_queue.py
│   ├── lock.py
│   └── logger.py
│
├── VIDEO_pipeline/
│   ├── pynqdpu.tf_yolov3_voc.DPUCZDX8G_ISA1_B4096.2.5.0.xmodel
│   └── yolo_DPU.py
│
├── config.yaml
├── CPSA_RUN.sh
├── main.py
└── README.md
```

---

# IMU Pipeline

The IMU pipeline processes synchronized BLE sensor streams coming from wearable devices.

Main functionalities:

* BLE acquisition
* dual-stream synchronization
* sliding window buffering
* quaternion alignment
* C-based feature extraction
* embedded classification
* event generation

The pipeline currently supports dual BlueCoin devices.

---

# VIDEO Pipeline

The system includes a camera-based parallel pipeline implemented in:

```bash
VIDEO_pipeline/yolo_DPU.py
```

This pipeline runs YOLOv3 inference on a USB camera stream using the Xilinx DPU runtime.

The pipeline:

* loads a compiled `.xmodel`
* initializes the XIR graph and VART DPU runner
* preprocesses webcam frames
* runs DPU inference
* performs YOLO postprocessing and NMS filtering
* detects person presence
* publishes results to the shared event system
* automatically deactivates after timeout if no person is detected

The DPU model path is loaded from the configuration system.

---

# DPU / Vitis-AI Setup

Reference repository:

[https://github.com/mdc-suite/VitisAI-based-applications/tree/main/dpu](https://github.com/mdc-suite/VitisAI-based-applications/tree/main/dpu)

## Additional Notes

Before calling `set_env.sh`:

Copy the archives from:

```bash
set_env/vitis_ai
```

to:

```bash
/home/$USER
```

---

## PythonPath Fix

If `vart` or `xir` cannot be imported:

```bash
echo 'export PYTHONPATH=/usr/lib/python3.10/site-packages:$PYTHONPATH' >> ~/.bashrc
source ~/.bashrc
```

---

## Running Python DPU Scripts

Pass the `.xmodel` file as argument:

```bash
python3 script.py -m /path/to/model.xmodel
```

---

## Load DPU Overlay on KV260

```bash
sudo xmutil loadapp kv260-benchmark-b4096
```

Do not specify the format extension, only the application name.

---

## Copy DPU Packages

Create target directory:

```bash
sudo mkdir -p /lib/firmware/xilinx/kv260-benchmark-b4096
```

Copy package contents:

```bash
sudo cp kv260-benchmark-b4096/* /lib/firmware/xilinx/kv260-benchmark-b4096/
```

---

# Bluetooth Setup (Kria KV260)

Tested Bluetooth adapter:

* ASUS USB-BT500

## Bluetooth Firmware Fix (Controller Not Detected)

The Bluetooth USB device may be recognized by the system, but the Bluetooth controller may not appear because the required firmware is missing.

### Verify Bluetooth Functionality

Start BlueZ:

```bash
bluetoothctl
```

Inside `bluetoothctl`:

```bash
list
```

The controller should appear.

Test scanning:

```bash
scan on
```

Stop scanning:

```bash
scan off
```

Exit:

```bash
quit
```

---

## If the Controller Does Not Appear

Some Bluetooth adapter revisions require manually installing firmware.

### Identify Missing Firmware

1. Connect the Bluetooth adapter.
2. Run:

```bash
sudo dmesg
```

3. Find the latest Bluetooth-related messages.
4. Look for missing firmware names such as:

```text
rtl_bt/rtl8761bu_fw.bin
```

or

```text
rtl_bt/rtl8761a_fw.bin
```

---

## Install Firmware

Install `wget`:

```bash
sudo apt install wget
```

Create firmware directory:

```bash
sudo mkdir -p /lib/firmware/rtl_bt
```

Example installation for `rtl8761bu_fw.bin`:

```bash
sudo wget -O /lib/firmware/rtl_bt/rtl8761bu_fw.bin \
https://www.lwfinger.com/download/rtl_bt/rtl8761bu_fw.bin
```

Example installation for `rtl8761a_fw.bin`:

```bash
sudo wget -O /lib/firmware/rtl_bt/rtl8761a_fw.bin \
https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/rtl_bt/rtl8761a_fw.bin
```

Reboot system:

```bash
sudo reboot
```

After reboot, verify Bluetooth functionality again using `bluetoothctl`.

---

# BlueST SDK Setup

Official repository:

[https://github.com/STMicroelectronics/BlueSTSDK_Python](https://github.com/STMicroelectronics/BlueSTSDK_Python)


Be careful to use the same Python version where dependencies were installed.

---

## BlueST SDK Dependencies

```bash
sudo apt install python3-pip python3-distutils libglib2.0-dev
```

```bash
pip install blue-st-sdk
pip install bluepy
pip install opuslib
```

---

## Grant Bluetooth Permissions to bluepy

```bash
sudo setcap "cap_net_raw+eip cap_net_admin+eip" \
/home/<user>/PycharmProjects/<project_name>/.venv/lib/python3.x/site-packages/bluepy/bluepy-helper
```

Important:

* there must NOT be commas inside the quoted string
* use normal quotes (`"`), not smart quotes

---

## Python 3.10 Compatibility Fix

Open:

```bash
/home/<user>/PycharmProjects/<project_name>/.venv/lib/python3.10/site-packages/blue_st_sdk/utils/dict_put_single_element.py
```

Modify line 43:

From:

```python
class DictPutSingleElement(collection.MutableMapping)
```

To:

```python
class DictPutSingleElement(collection.abc.MutableMapping)
```

---

## Add User to Bluetooth Group

Check current groups:

```bash
groups
```

If `bluetooth` is missing:

```bash
sudo usermod -aG bluetooth <username>
```

Reboot the system afterward.

---

# Adding Custom BlueCoin Features

Reference guide:

[https://github.com/STMicroelectronics/BlueSTSDK_Python#how-to-add-a-new-feature](https://github.com/STMicroelectronics/BlueSTSDK_Python#how-to-add-a-new-feature)

## Additional Notes

To add missing BlueCoin features not available in the Linux version of the BlueST SDK:

1. Create the feature implementation file.

Example:

```bash
sensors/BLE/feature_mems_sensor_fusion_compact.py
```

2. Open the BlueST SDK file:

```bash
/home/ubuntu/.local/lib/python3.10/site-packages/blue_st_sdk/utils/ble_node_definitions.py
```

3. Import the custom feature:

```python
from sensors.BLE import feature_mems_sensor_fusion_compact
```

4. Uncomment the corresponding feature tag:

```python
0x00000100: feature_mems_sensor_fusion_compact.FeatureMemsSensorFusionCompact,
```

Available features can be seen using the Android app ST BLE Sensor.

---

# How It Works

At runtime, the main process initializes:

- `SensorManager`
- `ActuatorManager`
- `EventDispatcher`
- `YoloDpuThread`

The architecture is designed to remain modular and extensible, allowing new sensing pipelines and actuators to be integrated independently from the event system.

---

# IMU Pipeline

The IMU pipeline processes synchronized BLE sensor streams coming from wearable BlueCoin devices.

The pipeline currently supports dual BlueCoin acquisition using:

- accelerometer
- gyroscope
- quaternion / sensor-fusion data

The sensor manager:

- scans for configured BlueCoin devices
- validates device presence before startup
- initializes one acquisition thread per device
- connects feature listeners to the synchronizer

Expected devices are defined in `config.yaml`:

```yaml
bluecoins:
  - id: bc_left
    name: "STOPmeL"

  - id: bc_right
    name: "STOPmeR"
```

Main pipeline stages:

```text
BlueCoin Threads
        ▼
Feature Listeners
        ▼
IMUSynchronizer
        ▼
DataBuffer
        ▼
C Processing
        ▼
StereotipyClassifier
        ▼
Shared Event Queue
```

---

## Synchronization

The `IMUSynchronizer` receives asynchronous IMU data from both wrists.

For each wrist, it waits for a complete triplet:

- accelerometer
- gyroscope
- quaternion

Synchronization constraints are configured in `config.yaml`:

```yaml
sync:
  max_skew_ms: 25
  stale_ms: 100
```

The synchronizer:

- aligns left and right wrist streams
- validates timestamp skew
- drops stale or misaligned triplets
- emits synchronized rows to the buffer

If synchronization fails, the older wrist sample is discarded to preserve real-time behavior.

---

## Buffering and Processing

The `DataBuffer` receives synchronized dual-wrist rows.

Each row contains:

```text
RIGHT: acc(3), gyr(3), quat(4)
LEFT : acc(3), gyr(3), quat(4)
```

The buffer uses configurable sliding windows:

```yaml
buffer:
  window_size: 150
  overlap: 75
```

When a window is ready, the buffer:

1. converts accelerometer values from `mg` to `m/s²`
2. aligns quaternion coordinates
3. skips the first window for stabilization
4. uses the second window for calibration
5. calls the C processing pipeline
6. generates an 18-feature vector

Processing is executed through:

```text
libProcessDataWristsQuat.so
```

The processing wrapper internally handles quaternion alignment and feature extraction.

---

## Classification

The `StereotipyClassifier` receives the processed feature vector and performs embedded inference through:

```text
libPredictPericolosaWristsQuat.so
```

The classifier generates a structured event containing:

- event ID
- timestamp
- source
- extracted features
- classification tag

Classification outputs:

```text
0 → NO_CLASS
1 → NON_DANGEROUS
2 → DANGEROUS
3 → NON_STEREOTIPY
```

Generated events are pushed into the shared event queue.

---

# VIDEO Pipeline

The system includes a camera-based parallel pipeline implemented in:

```bash
VIDEO_pipeline/yolo_DPU.py
```

This pipeline runs YOLOv3 inference on a USB camera stream using the Xilinx DPU runtime.

The YOLO thread is initialized at startup but remains idle until activated by the dispatcher.

The pipeline:

- loads a compiled `.xmodel`
- initializes the XIR graph and VART DPU runner
- opens the webcam only while active
- preprocesses webcam frames
- runs DPU inference
- performs YOLO postprocessing and NMS filtering
- detects person presence
- stores the latest detection result
- automatically deactivates after timeout if no person is detected

The current CPSA logic uses the VIDEO pipeline as a person-presence gate before allowing stereotypy actuation.

The DPU model path is loaded from the configuration system.

---

# Event System

The system uses a shared bounded queue for real-time event propagation.

Queue size is configurable:

```yaml
event_queue_size: 1
```

The queue is intentionally bounded to prioritize low latency over event retention.

If the queue becomes full:

- the oldest event is dropped
- the newest event replaces it

This prevents stale events from accumulating during overload conditions.

The event queue is shared across all pipelines and consumed by the dispatcher thread.

---

# Event Dispatcher

The `EventDispatcher` continuously consumes events from the shared queue.

For every event, the dispatcher:

1. reads the classification tag
2. converts the tag into a readable label
3. checks the latest YOLO detection result
4. activates or deactivates the VIDEO pipeline depending on the event type
5. decides whether actuation is allowed
6. calls the actuation policy
7. triggers the selected actuator through `ActuatorManager`
8. logs the event and actuation result

The dispatcher reacts immediately when the classification tag changes.

For repeated stereotypy tags (`1` or `2`), the dispatcher can retrigger actuation after a cooldown interval:

```python
ACTUATION_COOLDOWN = 5
```

If no person is detected by the VIDEO pipeline, stereotypy actuation can be blocked.

---

# Actuation Policy

The `StereotipyActivationPolicy` decides:

- which actuator to use
- how many retries to perform
- which variation parameters to apply

Policy configuration:

```yaml
policy:
  attempts: 3
```

The policy supports:

- actuator rotation
- retry logic
- variation cycling
- speaker cooldown handling
- severity-dependent feedback

Classification severity mapping:

```text
1 → mild / non-dangerous feedback
2 → strong / dangerous feedback
```

Actuator families are identified through runtime prefixes:

```text
led_      → Wi-Fi LED strip
meta_     → BLE MetaMotion
speaker_  → Bluetooth speaker
```

The policy dynamically changes parameters such as:

- LED colors and intensity
- vibration duration and duty cycle
- audio feedback selection

---

# Actuator Layer

The `ActuatorManager` dynamically scans, initializes, and controls enabled actuators.

Supported actuators:

- Wi-Fi LED strip
- BLE MetaMotion
- Bluetooth speaker

Each actuator runs in its own dedicated thread and exposes a common execution interface.

The dispatcher interacts only with the manager through:

```python
actuator_manager.trigger(...)
```

This abstraction keeps the event system independent from the underlying actuator implementations.

Actuator enable flags and device parameters are configured in `config.yaml`.

---

# Runtime Lifecycle

## Startup

At startup, the system:

1. initializes managers
2. scans sensors
3. validates required BlueCoin availability
4. scans enabled actuators
5. initializes sensor threads
6. initializes actuator threads
7. creates the actuation policy
8. starts the dispatcher thread
9. starts the YOLO DPU thread

If the required BlueCoin devices are not found after retry attempts, startup is aborted.

If no actuators are discovered, event detection and logging can still run.

---

## Shutdown

On termination, the system cleanly stops:

1. event dispatcher
2. YOLO DPU thread
3. sensor threads
4. actuator threads

This provides a centralized and thread-safe shutdown sequence for the runtime system.
---

# Logging

The system supports:

* internal system logs
* event tracking
* actuation tracking
* duration tracking

Logs can be exported in `.log` and `.csv` formats.

---

# Configuration

Main configuration file:

```bash
config.yaml
```

Configuration includes:

* device names and addresses
* synchronization parameters
* pipeline parameters
* classifier configuration
* actuator enable flags
* retry policy configuration
* logging settings
* DPU model path

---

# Usage

## Running the Main Runtime

The system entry point is:

```bash
main.py
```

The main runtime is responsible for:

- initializing the full CPSA system
- scanning sensors and actuators
- starting all runtime threads
- coordinating the event system
- managing shutdown

Run the system using:

```bash
python3 main.py
```

or:

```bash
bash CPSA_RUN.sh
```

---

## What `main.py` Does

The runtime flow inside `main.py` is:

```text
1. Initialize managers
2. Scan BLE sensors
3. Verify required BlueCoin devices
4. Scan actuators
5. Initialize sensors
6. Initialize actuators
7. Create actuation policy
8. Create YOLO DPU thread
9. Create event dispatcher
10. Start runtime threads
11. Keep system alive
12. Handle shutdown
```

---

## BlueCoin Configuration

The system expects the BlueCoin names configured in:

```yaml
bluecoins:
  - id: bc_left
    name: "STOPmeL"

  - id: bc_right
    name: "STOPmeR"
```

The names must match the actual BLE device names.

If one or more required BlueCoin devices are missing, startup is aborted.

---

## Enabling / Disabling Actuators

Actuators are enabled from `config.yaml`.

Example:

```yaml
speaker:
  enable: true

metamotion:
  enable: true

led_strip:
  enable: false
```

Disabled actuators are ignored during scanning and runtime.

---

## VIDEO Pipeline

The VIDEO pipeline is optional.

The DPU model path is configured through:

```yaml
dpu_model_name: "/path/to/model.xmodel"
```

The YOLO DPU thread is automatically started by `main.py`.

The camera pipeline remains idle until activated by the dispatcher.

---

## Runtime Behavior

Once started:

- BlueCoin devices continuously stream IMU data
- synchronized windows are processed
- the classifier generates events
- events are pushed into the shared queue
- the dispatcher applies the actuation policy
- actuators are triggered when conditions are satisfied

The main loop remains active until interrupted manually.

---

## Shutdown

Terminate the runtime with:

```bash
CTRL + C
```

`main.py` automatically performs a clean shutdown:

- dispatcher thread stopped
- YOLO DPU thread stopped
- sensor threads stopped
- actuator threads stopped
- BLE connections released
- camera resources released

---

# Adding New Sensors

Sensors are managed through `SensorManager`.

The current implementation is centered around BLE BlueCoin devices, but the architecture is modular and can be extended to support additional sensors and parallel sensing pipelines.

Current sensor pipeline structure:

```text
Sensor
    ▼
Feature Listener / Callback
    ▼
Synchronizer
    ▼
DataBuffer
    ▼
Processing
    ▼
Classifier
    ▼
Shared Event Queue
```

---

# Current BlueCoin Architecture

The current IMU implementation uses:

```text
sensors/BLE/bluecoin.py
sensors/BLE/feature_listeners.py
sensors/sensor_manager.py
```

The architecture is divided into:

- device discovery
- device thread management
- feature listeners
- synchronization
- buffering
- classification

---

# Sensor Types

A new sensor can be integrated in multiple ways:

| Type | Example |
|---|---|
| BLE wearable | BlueCoin, MetaWear |
| Wi-Fi sensor | network camera, ESP32 |
| USB / serial sensor | Arduino, biomedical devices |
| software pipeline | computer vision, external APIs |
| parallel event source | additional classifiers |

The sensor does not necessarily need to feed the IMU pipeline.

It can also publish events directly into the shared event queue.

---

# Sensor Module

Create a new sensor module in the correct category.

Examples:

```bash
sensors/BLE/new_sensor.py
sensors/WIFI/new_sensor.py
sensors/USB/new_sensor.py
```

Choose the folder based on the communication method.

---

# Scan Function

Sensors should provide a scan function similar to the existing BlueCoin implementation.

Current example:

```python
scan_bluecoin_devices(timeout)
```

The function should:

- discover compatible devices
- return device objects or identifiers
- handle scan exceptions internally
- avoid crashing the main runtime

Example:

```python
def scan_new_sensor_devices(timeout: int):
    """
    Scan for compatible sensor devices.
    """
    ...
```

Depending on the sensor type, the returned objects may be:

- BLE nodes
- MAC addresses
- serial ports
- IP addresses
- camera indexes
- SDK objects

---

# Sensor Thread

Each physical sensor should run in its own thread.

The current BlueCoin implementation uses:

```python
BlueCoinThread(threading.Thread)
```

Responsibilities:

- establish connection
- enable notifications or streams
- receive sensor updates
- reconnect automatically
- stop safely

Minimal structure:

```python
import threading

class NewSensorThread(threading.Thread):

    def __init__(self, device):
        super().__init__(daemon=True)

        self.device = device
        self.stop_event = threading.Event()

    def run(self):
        """
        Main acquisition loop.
        """
        ...

    def stop(self):
        """
        Stop the thread and release resources.
        """
        self.stop_event.set()

        if self.is_alive():
            self.join()
```

---

# Feature Listeners (BlueCoin-Specific)

The current BlueCoin implementation uses dedicated feature listeners:

```bash
sensors/BLE/feature_listeners.py
```

These listeners are specific to the BlueST SDK notification system.

Examples:

```python
AccelerometerFeatureListener
GyroscopeFeatureListener
QuaternionFeatureListener
```

Each listener:

- receives BLE notifications
- extracts feature values
- converts data to floats
- forwards samples to the synchronizer

Example:

```python
self.sync.update(
    self.device_id,
    "acc",
    values,
    ts=time.monotonic()
)
```

This listener architecture is BlueCoin-specific and is not mandatory for other sensors.

Other sensors may instead use:

- polling loops
- callbacks
- serial reads
- sockets
- SDK event systems

---

# Synchronizer Integration

If the new sensor must participate in synchronized IMU processing, it must integrate with:

```bash
IMU_pipeline/data_stream/synchronizer.py
```

Current synchronizer inputs:

```python
update(device_id, kind, values, ts)
```

Current supported kinds:

```text
acc
gyr
quat
```

The synchronizer aligns left and right wrist streams using:

```yaml
sync:
  max_skew_ms:
  stale_ms:
```

from `config.yaml`.

If the new sensor requires synchronization:

- add a new listener or callback
- define new feature types if needed
- extend synchronizer logic accordingly

---

# Feeding the Buffer

The synchronizer emits aligned rows into:

```bash
IMU_pipeline/data_stream/data_buffer.py
```

Current row format:

```text
RIGHT:
  acc(3)
  gyr(3)
  quat(4)

LEFT:
  acc(3)
  gyr(3)
  quat(4)
```

The buffer then:

- creates sliding windows
- applies preprocessing
- aligns quaternions
- calls the C processing pipeline
- forwards features to the classifier

If the new sensor changes the data structure, the following may require updates:

```text
synchronizer.py
data_buffer.py
C processing library
classifier wrapper
```

---

# Sensors That Do Not Use the IMU Pipeline

Not all sensors need synchronization or buffering.

Example:

```text
camera pipeline
radar pipeline
microphone pipeline
external AI model
```

These sensors can:

- process data independently
- generate events directly
- push events into the shared event queue

Current example:

```bash
VIDEO_pipeline/yolo_DPU.py
```

The vision pipeline runs independently from the IMU pipeline.

---

# Event Generation

Sensors or pipelines can publish events using:

```python
enqueue_drop_oldest(...)
```

from:

```bash
utils/event_queue.py
```

Example event structure:

```python
event = {
    "id": uuid.uuid4().hex,
    "timestamp": datetime.now().isoformat(),
    "source": "new_sensor",
    "stereotipy_tag": "1"
}
```

Events are consumed by:

```bash
core/event_dispatcher.py
```

---

# Registering the Sensor

To register a new sensor:

1. import the sensor module inside:

```bash
sensors/sensor_manager.py
```

2. add scan logic inside:

```python
scan_sensors()
```

3. add initialization logic inside:

```python
initialize_sensors()
```

4. start the sensor thread

Example:

```python
thread = NewSensorThread(device)
thread.start()
self.threads.append(thread)
```

---

# Configuration

Add sensor configuration inside:

```bash
config.yaml
```

Example:

```yaml
new_sensor:
  enable: true
  scan_timeout: 5
  retry_interval: 5
```

If needed, add helper functions inside:

```bash
utils/config.py
```

---

# Reconnection Handling

Wireless sensors should implement automatic reconnection.

Current BLE implementation uses:

```python
device_reconnection_lock
```

from:

```bash
utils.lock
```

This prevents multiple devices from reconnecting simultaneously.

Recommended pattern:

- fast retry loop
- slow retry loop
- interruptible waits
- graceful shutdown support

---

# Logging

Use:

```python
log_system(...)
```

for internal runtime messages.

Avoid excessive logging inside high-frequency callbacks.

---

# Implementation Checklist

To add a new sensor:

1. create the sensor module
2. implement device discovery
3. implement the acquisition thread
4. implement listeners or callbacks if needed
5. add reconnection logic if needed
6. register the sensor inside `SensorManager`
7. add configuration inside `config.yaml`
8. integrate with the synchronizer if required
9. integrate with the buffer if required
10. generate events or features
11. test the sensor independently
12. test the full pipeline integration

---

# Adding New Actuators

Actuators are managed through `ActuatorManager`.

Each actuator module should follow the same general structure used by the existing actuators:

- `actuators/BLE/metamotion.py`
- `actuators/BT/speaker.py`
- `actuators/WIFI/led_strip.py`

The common pattern is:

1. provide a scan function
2. implement a thread class
3. expose an `execute(...)` method
4. expose a `stop()` method
5. register the actuator inside `ActuatorManager`
6. add configuration in `config.yaml`
7. update the actuation policy if the actuator needs new parameters

---

## Actuator Module

Create a new file inside the correct actuator category.

Examples:

```bash
actuators/BLE/new_actuator.py
actuators/BT/new_actuator.py
actuators/WIFI/new_actuator.py
```

Choose the folder based on the communication method.

---

## Scan Function

Each actuator module should provide a scan function that returns device identifiers.

Examples from existing actuators:

```python
scan_metamotion_devices(timeout)  # returns BLE MAC addresses
scan_speaker_devices(timeout)     # returns Bluetooth MAC addresses
scan_led_devices(timeout)         # returns Wi-Fi IP addresses
```

The return value must be a list.

Example:

```python
def scan_new_actuator_devices(timeout: int) -> list[str]:
    """
    Scan for available actuator devices.

    Returns:
        list[str]: device identifiers such as MAC addresses or IP addresses.
    """
    ...
```

Depending on the actuator, the identifier can be:

- BLE MAC address
- Bluetooth MAC address
- IP address
- serial port
- logical device name

---

## Actuator Thread

Each actuator should run in its own thread.

The thread is responsible for:

- device connection
- waiting for commands
- executing actions
- handling reconnection if needed
- releasing resources during shutdown

Minimal structure:

```python
import threading

class NewActuatorThread(threading.Thread):
    def __init__(self, device_id: str):
        super().__init__(daemon=True)
        self.device_id = device_id
        self.stop_event = threading.Event()
        self.event = threading.Event()

    def run(self):
        """
        Connect to the actuator and wait for commands.
        """
        ...

    def execute(self, **kwargs):
        """
        Execute an actuator command.
        """
        ...

    def stop(self):
        """
        Stop the actuator thread and release resources.
        """
        self.stop_event.set()
        self.event.set()

        if threading.current_thread() is not self and self.is_alive():
            self.join()
```

---

## `execute(...)` Interface

Every actuator must expose an `execute(...)` method.

This is the method called by `ActuatorManager`.

The dispatcher does not call actuator-specific methods directly.

Runtime call chain:

```text
EventDispatcher
        ▼
StereotipyActivationPolicy
        ▼
ActuatorManager.trigger(...)
        ▼
actuator.execute(**params)
```

Existing examples:

```python
# MetaMotion
def execute(self, **kwargs):
    duty = kwargs.get("duty", 100)
    duration = kwargs.get("duration", 500)
    self.set_vibration(duty, duration)
```

```python
# Speaker
def execute(self, **kwargs):
    file = kwargs.get("file")
    self.file = file
    self.event.set()
```

```python
# LED strip
def execute(
    self,
    *,
    pattern=None,
    color=None,
    intensity=100,
    speed=100,
    duration=None,
):
    ...
```

The parameters accepted by `execute(...)` must match the parameters generated by the actuation policy.

---

## `stop()` Method

Every actuator must expose a `stop()` method.

It should:

- signal the thread to stop
- wake the thread if it is waiting
- cancel timers if used
- disconnect or release hardware resources
- join the thread safely

Example:

```python
def stop(self):
    self.stop_event.set()
    self.event.set()

    if threading.current_thread() is not self and self.is_alive():
        self.join()
```

---

## Reconnection Logic

Wireless actuators should handle disconnections internally.

Existing actuator examples use:

```python
device_reconnection_lock
```

from:

```python
utils.lock
```

This avoids multiple devices trying to reconnect at the same time.

Typical reconnection configuration is stored in `config.yaml`:

```yaml
fast_retry_attempts: 5
retry_interval: 5
retry_sleep: 60
```

Use this pattern for actuators that require persistent connections.

---

## Registering the Actuator

After implementing the actuator module, register it inside:

```bash
actuators/actuator_manager.py
```

Import the scan function and thread class:

```python
from actuators.WIFI.new_actuator import scan_new_actuator_devices, NewActuatorThread
```

Add fields inside `ActuatorManager.__init__()`:

```python
self.new_actuator_addresses = []
self.new_actuator_enable = False
```

Add scan logic inside `scan_actuators()`:

```python
self.new_actuator_enable = (get_new_actuator_config() or {}).get("enable", True)

if self.new_actuator_enable:
    with device_scan_lock:
        self.new_actuator_addresses = scan_new_actuator_devices(5) or []
```

Add initialization logic inside `initialize_actuators()`:

```python
if self.new_actuator_enable:
    for address in self.new_actuator_addresses:
        try:
            actuator_id = f"new_{address}"
            thread = NewActuatorThread(address)
            thread.start()
            self.actuators[actuator_id] = thread
            log_system(f"[ActuatorManager] New actuator initialized: {actuator_id}")
        except Exception as e:
            log_system(
                f"[ActuatorManager] New actuator {address} initialization failed: {e}",
                level="ERROR"
            )
```

---

## Actuator IDs

Each actuator is registered with a unique ID.

Current actuator ID prefixes:

```text
led_      → Wi-Fi LED strip
meta_     → BLE MetaMotion
speaker_  → Bluetooth speaker
```

New actuators should follow the same convention:

```text
<prefix>_<device_identifier>
```

Example:

```text
new_192.168.1.100
new_AA:BB:CC:DD:EE:FF
```

The prefix is important because the actuation policy uses it to decide which parameters to generate.

---

## Updating the Actuation Policy

If the new actuator needs custom parameters, update:

```bash
core/actuation_policy.py
```

Add a new branch inside `_params_for(...)`.

Example:

```python
elif actuator_id.startswith("new_"):
    params = {
        "param_1": value_1,
        "param_2": value_2,
    }
```

Then return:

```python
return {
    "actuator_id": actuator_id,
    "params": params,
}
```

The returned `params` dictionary is passed directly to:

```python
actuator.execute(**params)
```

---

## Configuration

Add a configuration section in:

```bash
config.yaml
```

Example:

```yaml
new_actuator:
  enable: true
  scan_timeout: 5
  fast_retry_attempts: 5
  retry_interval: 5
  retry_sleep: 60
```

If needed, add a helper function in:

```bash
utils/config.py
```

Example:

```python
def get_new_actuator_config():
    return get_config().get("new_actuator", {})
```

---

## Implementation Checklist

To add a new actuator:

1. create the actuator module
2. implement the scan function
3. implement the actuator thread
4. implement `execute(...)`
5. implement `stop()`
6. add configuration in `config.yaml`
7. add a config helper in `utils/config.py` if needed
8. import the actuator inside `ActuatorManager`
9. add scan logic inside `scan_actuators()`
10. add initialization logic inside `initialize_actuators()`
11. add policy parameter generation if needed
12. test the actuator independently
13. test it through the full dispatcher-policy-manager chain
---

# Modifying the Actuation Policy

The actuation policy defines how the system reacts to detected events.

The policy is responsible for:

- interpreting classifier outputs
- selecting which actuator to trigger
- generating actuator parameters
- retrying failed or ineffective feedback
- switching actuator strategies
- enforcing cooldown logic

Main implementation:

```bash
core/actuation_policy.py
```

The policy is executed by:

```bash
core/event_dispatcher.py
```

Runtime flow:

```text
Classifier
    ▼
Shared Event Queue
    ▼
EventDispatcher
    ▼
StereotipyActivationPolicy
    ▼
ActuatorManager
    ▼
Actuator.execute(...)
```

---

# Current Event Tags

Current classifier outputs:

| Tag | Meaning |
|---|---|
| `0` | No class |
| `1` | Non-dangerous stereotypy |
| `2` | Dangerous stereotypy |
| `3` | Non-stereotypy |

Defined in:

```python
TAG_NO_CLASS = 0
TAG_NON_DANGEROUS = 1
TAG_DANGEROUS = 2
TAG_NON_STEREOTIPY = 3
```

These values are used by:

- classifier
- dispatcher
- actuation policy

---

# Current Policy Behavior

Current logic:

- tags `1` and `2` trigger actuation
- tags `0` and `3` reset the policy state
- repeated events retry the same actuator
- after several attempts the policy switches actuator
- each actuator cycles through parameter variations

Example:

```text
dangerous event
    ▼
LED feedback
    ▼
same event persists
    ▼
different LED variation
    ▼
same event persists
    ▼
switch to speaker
```

---

# EventDispatcher Integration

The dispatcher consumes events from the shared queue:

```python
event = q.get(timeout=0.5)
```

Then calls:

```python
result = self.policy.handle(event)
```

The policy returns:

```python
{
    "actuator_id": actuator_id,
    "params": params
}
```

The dispatcher forwards the action to:

```python
self.actuator_manager.trigger(...)
```

---

# Adding New Event Classes

To support additional event types:

1. define a new tag constant
2. update label mappings
3. add policy handling logic
4. update the classifier output if needed

Example:

```python
TAG_STRESS = 4
```

Update dispatcher labels:

```python
LABELS = {
    ...
    4: "STRESS"
}
```

Then modify:

```python
handle(...)
```

inside:

```bash
core/actuation_policy.py
```

---

# Actuator Selection

The current implementation stores all available actuators:

```python
self.actuator_ids
```

Actuator selection is performed using:

```python
_pick_random(...)
```

Current actuator prefixes:

```text
led_
meta_
speaker_
```

The policy uses the prefix to determine which parameter set to generate.

Example:

```python
if actuator_id.startswith("led_"):
```

---

# Parameter Variations

Each actuator type defines multiple parameter variations.

Current examples:

```python
_led_variants_mild
_led_variants_strong

_meta_variants_mild
_meta_variants_strong

_spk_variants_mild
_spk_variants_strong
```

The policy cycles through these variations during repeated events.

Example:

```python
{"color": (255,0,0,0), "intensity":100}
```

or:

```python
{"duty":100, "duration":900}
```

These dictionaries are passed directly to:

```python
actuator.execute(**params)
```

---

# Adding Support for New Actuators

If a new actuator is added, update:

```python
_params_for(...)
```

Example:

```python
elif actuator_id.startswith("new_"):
    variants = self._new_variants_mild if mild else self._new_variants_strong

    params = variants[
        variation_index % len(variants)
    ]
```

Then return:

```python
return {
    "actuator_id": actuator_id,
    "params": params
}
```

---

# Retry Logic

The current policy retries the same actuator before switching.

Configured by:

```yaml
policy:
  attempts: 3
```

from:

```bash
config.yaml
```

Internal state:

```python
self._attempts_on_current
```

Once the retry limit is reached:

```python
self._current_actuator = self._pick_random(
    exclude=self._current_actuator
)
```

---

# Variation Cycling

Each actuator maintains its own variation index.

Example:

```python
self._variation_idx_per_actuator
```

This allows parameter progression independently for each actuator.

Example:

```text
LED:
  variation 1
  variation 2
  variation 3

Speaker:
  variation 1
  variation 2
```

---

# Cooldowns

The policy can enforce cooldowns.

Current example:

```python
self._spk_cooldown_sec = 5
```

Used to avoid excessive audio feedback.

Cooldown checks occur before actuation generation.

Example:

```python
if now - last < self._spk_cooldown_sec:
    return None
```

---

# Reset Logic

When the classifier returns:

```text
0 -> NO_CLASS
3 -> NON_STEREOTIPY
```

the policy resets internal state:

```python
_reset_state()
```

This clears:

- current actuator
- retry counters
- active event state

The LED actuator additionally receives an OFF command.

---

# Dispatcher Cooldown

The dispatcher itself also contains retry timing logic.

Defined in:

```python
ACTUATION_COOLDOWN = 5
```

inside:

```bash
core/event_dispatcher.py
```

This prevents continuous retriggering at every incoming event.

---

# Vision-Based Gating

The dispatcher optionally integrates with the YOLO DPU pipeline.

Current logic:

```python
person_detected, _ = self.yolo_thread.get_latest_result()
```

If no person is detected:

```python
result = None
```

and actuation is blocked.

This allows sensor detections to be conditionally validated by external pipelines.

---

# Extending Policy Logic

The policy can be extended with:

- adaptive feedback scoring
- reinforcement learning
- patient-specific adaptation
- time-based escalation
- multimodal coordination
- context-aware filtering
- actuator effectiveness memory
- confidence-based feedback
- pipeline fusion logic

The architecture is intentionally modular to support future experimentation.

---

# Implementation Checklist

To modify the actuation policy:

1. update event definitions if needed
2. modify `handle(...)`
3. modify `_params_for(...)`
4. add parameter variants
5. update cooldown logic if needed
6. update retry logic if needed
7. verify actuator compatibility
8. test through `EventDispatcher`
9. test full runtime behavior
---

# Author

Francesco Urru

[https://github.com/frarvo](https://github.com/frarvo)
