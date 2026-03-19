# data_pipeline/synchronizer.py
# Align LEFT/RIGHT IMU data (acc, gyr, quat) by timestamp skew and emit joint rows.
#
# Author: Francesco Urru
# Github: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

from utils.logger import log_system
from utils.config import get_bluecoin_config, get_sync_config
from data_pipeline.data_buffer import DataBuffer

Vec3 = Tuple[float, float, float]
Quat = Tuple[float, float, float, float]

@dataclass
class _DevState:
    acc:  Optional[Vec3]  = None
    gyr:  Optional[Vec3]  = None
    quat: Optional[Quat]  = None
    ts_acc:  float = 0.0
    ts_gyr:  float = 0.0
    ts_quat: float = 0.0

    def ready(self) -> bool:
        return (self.acc is not None) and (self.gyr is not None) and (self.quat is not None)

    def newest_ts(self) -> float:
        return max(self.ts_acc, self.ts_gyr, self.ts_quat)

    def clear_triplet(self) -> None:
        self.acc = self.gyr = self.quat = None
        self.ts_acc = self.ts_gyr = self.ts_quat = 0.0


class IMUSynchronizer:
    """
    Takes configurations for bluecoins and IMUs from config.yaml
    Receives data from listeners via update(device_id, kind, values, ts)
    Aligns wrists within max_skew_ms, then pushes one row to DataBuffer:
        buffer.add_buffer_row(R_acc, R_gyr, R_quat, L_acc, L_gyr, L_quat, ts_emit)
    """

    def __init__(self):
        sync_cfg = get_sync_config() or {}

        # Timing and alignment settings
        self.max_skew = max(0, int(sync_cfg.get("max_skew_ms", 25))) / 1000.0  # seconds
        self.stale = max(0, int(sync_cfg.get("stale_ms", 0))) / 1000.0

        # Determine left/right device IDs from bluecoins section of config.yaml
        bc = get_bluecoin_config() or []
        ids = [e.get("id") for e in bc if isinstance(e, dict) and e.get("id")]

        self.left_id, self.right_id = "bc_left", "bc_right"

        log_system(f"[IMUSync] Init: L={self.left_id} R={self.right_id} "
                   f"skew={int(self.max_skew*1000)}ms stale={'off' if self.stale==0 else str(int(self.stale*1000))+'ms'}")

        # Shared state and buffer
        self._lock = threading.Lock()
        self._state: Dict[str, _DevState] = {
            self.left_id:  _DevState(),
            self.right_id: _DevState(),
        }
        # Buffer instance
        self.buffer = DataBuffer()

        # stats (optional)
        self._emits = 0
        self._drops_left = 0
        self._drops_right = 0

        self._pending_row = None

    # Public call for listeners
    def update(self, device_id: str, kind: str, values, ts: float) -> None:
        """
        device_id must match one of the configured ids (e.g., 'bc_left'/'bc_right').
        kind: {'acc','gyr','quat'}.
        values: 3-tuple for acc/gyr, 4-tuple for quat.
        ts: time.monotonic() at arrival.
        """
        if device_id not in self._state:
            return

        row = None
        with self._lock:
            st = self._state[device_id]
            try:
                if kind == "acc":
                    st.acc = (float(values[0]), float(values[1]), float(values[2])); st.ts_acc = ts
                elif kind == "gyr":
                    st.gyr = (float(values[0]), float(values[1]), float(values[2])); st.ts_gyr = ts
                elif kind == "quat":
                    st.quat = (float(values[0]), float(values[1]), float(values[2]), float(values[3])); st.ts_quat = ts
                else:
                    return
            except Exception as e:
                log_system(f"[IMUSync] Bad {kind} for {device_id}: {e}", level="WARNING")
                return

            self._try_emit_locked()
            row = self._pending_row
            self._pending_row = None
            if row:
                (Racc, Rgyr, Rquat, Lacc, Lgyr, Lquat, ts_emit) = row
                self.buffer.add_buffer_row(Racc, Rgyr, Rquat, Lacc, Lgyr, Lquat, ts_emit)

    # Internals (lock held)
    # Push synced row to buffer
    def _try_emit_locked(self) -> None:
        L = self._state[self.left_id]
        R = self._state[self.right_id]

        # Optional stale protection
        if self.stale > 0.0:
            now = time.monotonic()
            if L.ready() and (now - L.newest_ts() > self.stale):
                L.clear_triplet(); self._drops_left += 1
            if R.ready() and (now - R.newest_ts() > self.stale):
                R.clear_triplet(); self._drops_right += 1

        if not (L.ready() and R.ready()):
            return

        tL, tR = L.newest_ts(), R.newest_ts()
        if abs(tL - tR) <= self.max_skew:
            try:
                ts_emit = max(tL, tR)
                # RIGHT first then LEFT, then timestamp
                row = (R.acc, R.gyr, R.quat, L.acc, L.gyr, L.quat, ts_emit)
                self._emits += 1
                L.clear_triplet()
                R.clear_triplet()
            except Exception as e:
                log_system(f"[IMUSync] add_buffer_row error: {type(e).__name__}: {e}", level="ERROR")
        else:
            # Not aligned: drop the older triplet to resync quickly
            if (tL + self.max_skew) < tR:
                L.clear_triplet()
                self._drops_left += 1
            elif (tR + self.max_skew) < tL:
                R.clear_triplet()
                self._drops_right += 1
            row = None

        self._pending_row = row

    # optional helpers
    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return {"emits": self._emits, "drops_left": self._drops_left, "drops_right": self._drops_right}

    def reset(self) -> None:
        with self._lock:
            self._state[self.left_id].clear_triplet()
            self._state[self.right_id].clear_triplet()
            self._emits = self._drops_left = self._drops_right = 0