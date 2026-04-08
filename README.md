# CPSA_2026
Modular Python Cyber-Physical system for real-time feedback 
using wireless BLE sensors and actuators.

CPSA_2026 is a modular and extensible Cyber-Physical system designed to 
connect wearable BLE sensors and multisensory actuators to provide real-time, 
adaptive feedback based on detected motion patterns.

This project evolves from the STOPme prototype, which focuses on real-time detection 
of motion-based events using dual-wrist IMU sensors and reactive actuation. 

CPSA_2026 extends this foundation by integrating additional sensing modalities, 
such as a camera for real-time vision-based detection,
and a custom DPU-accelerated model for <blank> recognition. 
The system maintains a fully decoupled, event-driven architecture, 
combining synchronized multi-sensor data, C-based processing pipelines, 
and structured actuation logic.

---

## Features

- Real-time acquisition from BLE IMU devices (dual BlueCoin)
- Dual-wrist synchronization with configurable timing tolerance
- Sliding window buffering with overlap
- C-based feature extraction
- Embedded classifier (C library integration)
- Event-driven architecture with bounded queue
- Modular actuator control:
  - Wi-Fi LED strip
  - BLE haptic device (MetaMotion)
  - Bluetooth speaker
- Adaptive actuation policy with retry and variation logic
- Thread-safe logging with event duration tracking
- Automatic device reconnection handling
- Scalable, testable, and maintainable architecture

---

## System Overview

```
BlueCoin Sensors (Left / Right)
        ↓
IMU Synchronizer
        ↓
Sliding Window Buffer
        ↓
C Processing (Feature extraction)
        ↓
Classifier (Detection) ──────────→ Stereotipy Diary
        ↓
Event Queue
        ↓
Event Dispatcher
        ↓
Actuation Policy
        ↓
Actuators (LED / Vibration / Audio)
```

---

## Requirements

### Operating System

Tested on:
- Operating system:     Ubuntu 22.04 
- Kernel: 5.15.0-1067-xilinx-zynqmp

NOTES:
- Newer Ubuntu versions may introduce BLE stack incompatibilities.

---

### Python Version

Tested on:
- Python 3.10

---

### pip Version

- pip 22.0.2

---

## System Dependencies

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

## Python Dependencies

Install in the following order.

### BlueST SDK (BlueCoin)

```bash
pip install blue-st-sdk
```

---

### bluepy

```bash
pip install bluepy
```

Grant BLE permissions:

```bash
sudo setcap "cap_net_raw+eip cap_net_admin+eip" \
/home/$USER/.local/lib/python3.10/site-packages/bluepy/bluepy-helper
```
Check if applied with:
```bash
sudo getcap /home/$USER/.local/lib/python3.10/site-packages/bluepy/bluepy-helper
```
NOTES:
- If command setcap doesn't work, make sure you are using 
straight double quotes "" or '', not smart quotes “”.

---

### MetaMotion SDK

```bash
pip install metawear
```

---

### PyWarble (SIGNIFICANT)

PyWarble is an automatic installed dependency for MetaMotion SDK.

The default RELEASE version may cause buffer overflow issues, 
DEBUG version resolves this issue.

```bash
pip uninstall warble
git clone --recurse-submodules https://github.com/mbientlab/PyWarble.git
cd PyWarble
```

Modify `setup.py`:

Change:
```python
args = ["make", "-C", warble, "-j%d" % (cpu_count())]
```

To:
```python
args = ["make", "-C", warble, "CONFIG=debug", "-j%d" % (cpu_count())]
```

And change:
```python
so = os.path.join(warble, 'dist', 'release', 'lib', machine)
```

To:
```python
so = os.path.join(warble, 'dist', 'debug', 'lib', machine)
```

Then reinstall manually while inside the PyWarble folder:

```bash
pip install .
```

Verify installation:

```bash
pip list
```
PyWarble 1.2.8 should appear instead of 1.2.9.

---

### Other Python Dependencies

```bash
pip install numpy pyyaml playsound flux_led opuslib
```

---

## Project Structure

```bash
CPSA_2026/
├── main.py
├── config.yaml
├── CPSA_RUN.sh

├── actuators/
│   ├── actuator_manager.py
│   ├── led_strip.py
│   ├── metamotion.py
│   └── speaker.py

├── assets/
│   └── audio/
│   │   └── *.mp3 (Audio files)

├── classifiers/
│   ├── stereotipy_classifier.py
│   ├── predict_models_wrapper_quat.py
│   ├── libPredictPericolosaWristsQuat.so
│   └── Predict_Pericolosa_Wrists_Quat
│   │   └── * source files for libPredictPericolosaWristsQuat.so binary build

├── core/
│   ├── actuation_policy.py
│   └── event_dispatcher.py

├── data_pipeline/
│   ├── data_buffer.py
│   ├── synchronizer.py
│   ├── data_processing_wrapper_quat.py
│   ├── libProcessDataWristsQuat.so
│   └── ProcessDataWristsQuat
│   │   └── * source files for libProcessDataWristsQuat.so binary build

├── sensors/
│   ├── bluecoin.py
│   ├── sensor_manager.py
│   ├── feature_listeners.py
│   └── feature_mems_sensor_fusion_compact.py

├── utils/
│   ├── config.py
│   ├── logger.py
│   ├── lock.py
│   ├── event_queue.py
│   └── audio_paths.py
```

---

## How It Works

### Sensor Layer
BlueCoin devices stream accelerometer, gyroscope, and quaternion data.

### Synchronization
Aligns left and right wrist data streams and enforces timing constraints.

### Buffer & Processing
- Sliding window (default: 150 samples, 50% overlap)
- Data normalization and quaternion alignment
- Feature extraction via C library

### Classification
Outputs:
- 0 → No class  
- 1 → Non-dangerous stereotypy  
- 2 → Dangerous stereotypy  
- 3 → Non-stereotypy  

### Event System
- Events are stored in a bounded queue
- Oldest events are dropped if overloaded (real-time priority)

### Dispatcher
Consumes events, logs them, and triggers actions.

### Actuation Policy
- Selects actuator based on event severity
- Applies retries and parameter variations
- Switches actuator after defined attempts

### Actuators
- LED strip (Wi-Fi)
- MetaMotion (BLE vibration)
- Bluetooth speaker

---

## Configuration

All system parameters are defined in:

```
config.yaml
```

Includes:
- Expected device names or mac addresses
- Buffer parameters
- Synchronization thresholds
- Actuator enable flags
- Policy attempts configuration
- Logging settings

---

## Logging

### System Log
- Internal system events and errors

### Event Diary
- Detected events
- Triggered actuations
- Duration tracking

Logs are stored per day in `.log` and `.csv` format.

---

## Running the System

```bash
bash CPSA_RUN.sh 
```
or
```bash
./CPSA_RUN.sh 
```
or
```bash
python3 main.py
```


---
## How to Add bluetooth drivers to kria board
dd


---
## Adding a new Actuator
dd


---
## Adding a new Sensor
dd


---
## Adding a new feature to BlueCoin (To use integrated sensors not already available in linux version of BlueST-SDK)
### How to create the feature for the desired sensor
Follow the guide at https://github.com/STMicroelectronics/BlueSTSDK_Python?tab=readme-ov-file#how-to-add-a-new-feature
feature_mems_sensor_fusion_compact.py

### How to add the feature to the Blue-ST-SDK
Open the file at this path: 
python3.10/site-packages/blue_st_sdk/utils/ble_node_definitions.py

Import the file created previously:
from sensors import feature_mems_sensor_fusion_compact

Remove the comment relative to the desired feature: 
0x00000100: feature_mems_sensor_fusion_compact.FeatureMemsSensorFusionCompact,

---
## How to use 
dd



---



## Author

Francesco Urru
https://github.com/frarvo
