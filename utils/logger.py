import os
from datetime import datetime
from pathlib import Path
from utils.lock import logging_lock
from utils.config import (
    get_log_path,
    actuation_details_enabled,
    system_log_enabled,
    debug_system_console_enabled,
    debug_event_console_enabled
)

def _ensure_dir(path: Path):
    """Ensure a directory exists, create it if needed."""
    os.makedirs(path, exist_ok=True)

def _get_day_folder(base_dir: Path) -> Path:
    """
    Return today's log directory as a Path.
    Create the directory if it doesn't exist.
    """
    day_folder = datetime.now().strftime("%d-%m-%Y")
    full_path = base_dir / day_folder
    _ensure_dir(full_path)
    return full_path

def log_events(timestamp: str, feature_type: str, event: str, actuations: list, source: str):
    """
    Log a sensor event to both .log and .csv files.

    Parameters:
        timestamp (str): ISO8601 timestamp
        feature_type (str): e.g., 'temperature', 'activity'
        event (str): e.g., 'WALKING', 'TEMP_HIGH'
        actuations (list): list of dicts with 'target' and 'params'
        source (str): sensor name, e.g., 'BC_Temperature'
    """
    log_base = Path(get_log_path())
    folder = _get_day_folder(log_base)

    date_str = datetime.fromisoformat(timestamp).strftime("%d-%m-%Y")
    time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")

    actions = []
    for action in actuations:
        target_name = action["target"].upper()
        if actuation_details_enabled():
            params = action.get("params", {})
            param_str = ", ".join(f"{key}={value}" for key, value in params.items())
            formatted = f"{target_name}({param_str})"
        else:
            formatted = target_name
        actions.append(formatted)
    action_str = ", ".join(actions)

    log_filename = f"Event_Diary_{source}.log"
    log_path = folder / log_filename
    line_txt = f"[{date_str} {time_str}] - {feature_type.upper()} - {event} - {action_str}\n"

    with logging_lock:
        with open(log_path, "a") as f:
            f.write(line_txt)

    if debug_event_console_enabled():
        print(line_txt.strip())

    csv_filename = f"Event_Diary_{source}.csv"
    csv_path = folder / csv_filename
    header = "date,timestamp,feature,event,actuation\n"
    line_csv = f"{date_str},{time_str},{feature_type},{event},\"{action_str}\"\n"

    write_header = not csv_path.exists()
    with logging_lock:
        with open(csv_path, "a") as f:
            if write_header:
                f.write(header)
            f.write(line_csv)

def log_system(message: str, level: str = "INFO"):
    """
    Log a system-level message to the system log file.

    Parameters:
        message (str): Log message
        level (str): One of 'INFO', 'WARNING', 'ERROR'
    """
    date = datetime.now().strftime("%d-%m-%Y")
    time = datetime.now().strftime("%H:%M:%S")
    line = f"[{date} {time}] - {level.upper()} - {message}\n"

    if debug_system_console_enabled():
        print(line.strip())

    if not system_log_enabled():
        return

    log_base = Path(get_log_path())
    folder = _get_day_folder(log_base)
    filepath = folder / "System_Log.log"
    with logging_lock:
        with open(filepath, "a") as f:
            f.write(line)

_last_event_timestamp: datetime = None
_last_event_file: Path = None
_last_event_line_idx: int = None

def log_event(timestamp: str,
              feature_type: str,
              event: str,
              actuations: list,
              source: str):
    """
    Log a new sensor event to file, and retroactively add duration to the previous one if it exists.

    Parameters:
        timestamp (str): ISO8601 timestamp
        feature_type (str): 'temperature' or 'activity'
        event (str): event label
        actuations (list): list of dicts with 'target' and 'params'
        source (str): e.g. 'BC_Temperature'
    """
    global _last_event_timestamp, _last_event_file, _last_event_line_idx

    log_base = Path(get_log_path())
    folder = _get_day_folder(log_base)

    log_filename = f"Event_Diary_{source}.log"
    log_path = folder / log_filename
    csv_filename = f"Event_Diary_{source}.csv"
    csv_path = folder / csv_filename

    try:
        now = datetime.fromisoformat(timestamp)
    except Exception:
        now = datetime.now()

    date_str = now.strftime("%d-%m-%Y")
    time_str = now.strftime("%H:%M:%S")

    actions = []
    for action in actuations:
        target_name = action["target"].upper()
        if actuation_details_enabled():
            params = action.get("params", {})
            param_str = ", ".join(f"{k}={v}" for k, v in params.items())
            formatted = f"{target_name}({param_str})"
        else:
            formatted = target_name
        actions.append(formatted)
    action_str = ", ".join(actions)

    if (_last_event_timestamp is not None and
        _last_event_file is not None and
        _last_event_line_idx is not None):

        prev_log_path = _last_event_file
        with logging_lock:
            with open(prev_log_path, "r") as f_log:
                log_lines = f_log.readlines()

        if 0 <= _last_event_line_idx < len(log_lines):
            delta = now - _last_event_timestamp
            total_seconds = int(delta.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            duration_str = f"{minutes:02d}:{seconds:02d}"

            old_log_line = log_lines[_last_event_line_idx].rstrip("\n")
            log_lines[_last_event_line_idx] = old_log_line + f" - Duration: {duration_str}\n"

            with logging_lock:
                with open(prev_log_path, "w") as f_log:
                    f_log.writelines(log_lines)

            prev_csv_path = prev_log_path.with_suffix(".csv")
            if not prev_csv_path.exists():
                header = "date,timestamp,feature,event,actuation,duration\n"

                with logging_lock:
                    with open(prev_csv_path, "w") as f_csv:
                        f_csv.write(header)

            with logging_lock:
                with open(prev_csv_path, "r") as f_csv:
                    csv_lines = f_csv.readlines()

            prev_csv_idx = _last_event_line_idx + 1
            if 0 <= prev_csv_idx < len(csv_lines):
                old_csv_line = csv_lines[prev_csv_idx].rstrip("\n")
                csv_lines[prev_csv_idx] = old_csv_line + f",{duration_str}\n"
                with logging_lock:
                    with open(prev_csv_path, "w") as f_csv:
                        f_csv.writelines(csv_lines)
            else:
                log_system("[logger] CSV line index out of range; skipping duration update", level="WARNING")
        else:
            log_system("[logger] Log line index out of range; skipping duration update", level="WARNING")

    line_txt = f"[{date_str} {time_str}] - {feature_type.upper()} - {event} - {action_str}\n"
    with logging_lock:
        with open(log_path, "a") as f_log:
            f_log.write(line_txt)

    if debug_event_console_enabled():
        print(line_txt.strip())

    if not csv_path.exists():
        header = "date,timestamp,feature,event,actuation,duration\n"
        with logging_lock:
            with open(csv_path, "w") as f_csv:
                f_csv.write(header)

    csv_line = f"{date_str},{time_str},{feature_type},{event},\"{action_str}\",\n"

    with logging_lock:
        with open(csv_path, "a") as f_csv:
            f_csv.write(csv_line)

    try:
        with logging_lock:
            with open(log_path, "r") as f:
                log_lines = f.readlines()
        prev_count = len(log_lines) - 1
    except Exception:
        prev_count = 0

    _last_event_timestamp = now
    _last_event_file = log_path
    _last_event_line_idx = prev_count


