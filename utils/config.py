# config.py
# Extract configuration variables from config.yaml file to python
#
# Author: Francesco Urru
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/CPSA_2026
# License: MIT

import os
from pathlib import Path
import yaml
from os.path import expanduser

# ---- CONFIG LOCATION (robust) ----
CONFIG_FILENAME = "config.yaml"

def _discover_config_path() -> Path:
    """
    Resolve the path to config.yaml with this priority:
      1) STOPME_CONFIG env var (absolute or relative)
      2) Walk upwards from this file's directory until config.yaml is found
      3) Current working directory (if it has config.yaml)
    """
    # 1) Environment variable override
    env_path = os.getenv("STOPME_CONFIG")
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_file():
            return p

    # 2) Walk up parents from this file
    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        candidate = parent / CONFIG_FILENAME
        if candidate.is_file():
            return candidate

    # 3) Check CWD as a last resort
    cwd_candidate = Path.cwd() / CONFIG_FILENAME
    if cwd_candidate.is_file():
        return cwd_candidate

    # Fallback to expected repo root two levels up (works for old layout)
    return here.parents[2] / CONFIG_FILENAME

CONFIG_PATH = _discover_config_path()

# ---- LOAD CONFIG ----
try:
    with open(CONFIG_PATH, "r") as f:
        CONFIG = yaml.safe_load(f) or {}
    if not isinstance(CONFIG, dict):
        CONFIG = {}
except Exception:
    CONFIG = {}

# LOGGER
def get_log_path():
    """
    Returns the resolved base log path, expanding "~" to the user's home directory.
    """
    default_base = str(Path.home() / "Documents" / "STOPME" / "logs")
    return str(Path(expanduser(CONFIG.get("log_base_path", default_base))))

def actuation_details_enabled() -> bool:
    return CONFIG.get("enable_actuation_detail", True)

def system_log_enabled() -> bool:
    return CONFIG.get("enable_system_log", True)

def debug_system_console_enabled() -> bool:
    return CONFIG.get("debug_system_console", False)

def debug_event_console_enabled() -> bool:
    return CONFIG.get("debug_event_console", False)

# METAMOTION
def get_metamotion_config() -> dict:
    return CONFIG.get("metamotion", {})

# SPEAKER
def get_speaker_config() -> dict:
    return CONFIG.get("speaker", {})

# LED_STRIP
def get_led_strip_config() -> dict:
    return CONFIG.get("led_strip", {})

# BLUECOIN
def get_bluecoin_config() -> list[dict]:
    return CONFIG.get("bluecoins", []) or []

# IMU CONFIGURATION
def get_sync_config() -> dict:
    sync_cfg = CONFIG.get("sync", {}) or {}
    return {
        "max_skew_ms": int(sync_cfg.get("max_skew_ms", 25)),
        "stale_ms": int(sync_cfg.get("stale_ms", 100)),
    }

# BUFFER CONFIGURATION
def get_buffer_config() -> dict:
    buff_cfg = CONFIG.get("buffer", {}) or {}
    return {
        "window_size": int(buff_cfg.get("window_size", 150)),
        "overlap": int(buff_cfg.get("overlap", 75)),
        "debug_print_buffer": bool(buff_cfg.get("debug_print_buffer", True)),
        "debug_print_features": bool(buff_cfg.get("debug_print_features", True)),
    }

# POLICY CONFIGURATION
def get_policy_attempts() -> int:
    policy_config = CONFIG.get("policy", {}) or {}
    return int(policy_config.get("attempts", 5))

# QUEUE SIZE
def get_event_queue_size() -> int:
    return int(CONFIG.get("event_queue_size", 5))

# MODEL PATH
def get_dpu_path() -> str:
    return str(Path(CONFIG["dpu_model_name"]).expanduser())
