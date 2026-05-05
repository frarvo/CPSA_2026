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

Documentation will be added later.

---

# Adding New Actuators

Documentation will be added later.

---

# Author

Francesco Urru

[https://github.com/frarvo](https://github.com/frarvo)
