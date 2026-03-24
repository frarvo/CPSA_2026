# data_pipeline/data_buffer.py
# Sliding window buffer for dual wrist BlueCoin (Right+Left).
#
# Each incoming row (from synchronizer) is 20 floats in this exact order:
#   RIGHT: acc(3), gyr(3), quat(4)  -> 0..9
#   LEFT : acc(3), gyr(3), quat(4)  -> 10..19
#
# Author: Francesco Urru
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/CPSA_2026
# License: MIT

from __future__ import annotations

import math
from typing import List, Tuple, Callable, Optional
import threading
import numpy as np

from utils.logger import log_system
from utils.config import get_buffer_config
from data_pipeline.data_processing_wrapper_quat import process_data_wrists_quat, initialize as init_process

Vec3  = Tuple[float, float, float]
Quat4 = Tuple[float, float, float, float]

G_TO_MPS2 = 9.80665
DPS_TO_RAD_S = math.pi / 180.0

class DataBuffer:
    """
    Collects aligned wrists data rows from synchronizer and emits sliding windows for processing.

    Usage:
      - synchronizer calls add_buffer_row(R_acc, R_gyr, R_quat, L_acc, L_gyr, L_quat, ts)
      - when a full window is ready buffer will:
          * build 20 explicit np.float32 vectors (length = window_size)
          * scale accel mg -> g
          * call process_data_wrists_quat(...)
          * push features (np.float32[18]) to the recognizer (trained classifier)
    """

    def __init__(self,
                 window_size: Optional[int] = None,
                 hop_size:    Optional[int] = None):
        cfg = get_buffer_config() or {}

        # Get Window size and hop_size from config.yaml
        self.window_size = int(window_size if window_size is not None else cfg.get("window_size", 150))
        self.hop_size    = int(hop_size    if hop_size    is not None else cfg.get("overlap", 75))
        self._debug_print_buffer = bool(cfg.get("debug_print_buffer", False))
        self._debug_print_features = bool(cfg.get("debug_print_features", False))

        # Storage (rows and timestamps are parallel)
        self._rows: List[Tuple[float, ...]] = []   # each row has 20 floats (collected in a Tuple)
        self._ts:   List[float] = []               # one ts per row (separate list)
        self._lock = threading.Lock()

        # Optional consumer for features (np.float32[18])
        self._features_sink: Optional[Callable[[np.ndarray, float], None]] = None
        self._windows_emitted = 0

        # Calibrated flag
        self._calibrated = False

        log_system(f"[DataBuffer] init: window= {self.window_size} hop= {self.hop_size}")
        init_process()

    # Public API for external use

    def add_buffer_row(self,
                       R_acc: Vec3, R_gyr: Vec3, R_quat: Quat4,
                       L_acc: Vec3, L_gyr: Vec3, L_quat: Quat4,
                       ts_emit: float) -> None:
        """
        Append one row to the buffer (order must match).
        Cast to float to match processing requirements
        """
        window_rows = None
        window_ts = None
        row = (
            float(R_acc[0]), float(R_acc[1]), float(R_acc[2]),                      # RIGHT acc_x, acc_y, acc_z
            float(R_gyr[0]), float(R_gyr[1]), float(R_gyr[2]),                      # RIGHT gyr_x, gyr_y, gyr_z
            float(R_quat[0]), float(R_quat[1]), float(R_quat[2]), float(R_quat[3]), # RIGHT quat_x, quat_y, quat_z, quat_w

            float(L_acc[0]), float(L_acc[1]), float(L_acc[2]),                      # LEFT acc_x, acc_y, acc_z
            float(L_gyr[0]), float(L_gyr[1]), float(L_gyr[2]),                      # LEFT gyr_x, gyr_y, gyr_z
            float(L_quat[0]), float(L_quat[1]), float(L_quat[2]), float(L_quat[3]), # LEFT quat_x, quat_y, quat_z, quat_w
        )

        with self._lock:
            self._rows.append(row)
            self._ts.append(float(ts_emit))

            if len(self._rows) >= self.window_size:
                start = len(self._rows) - self.window_size
                window_rows = self._rows[start : start + self.window_size]
                window_ts   = self._ts[start   : start + self.window_size]

                # Slide forward by hop
                keep_from = self.hop_size
                if keep_from <= 0:
                    # safety fallback: clear to avoid stall
                    self._rows.clear()
                    self._ts.clear()
                else:
                    self._rows = self._rows[keep_from:]
                    self._ts   = self._ts[keep_from:]

        if window_rows is not None:
            self._on_window_ready(window_rows, window_ts)

    def set_features_sink(self, sink: Callable[[np.ndarray, float], None]) -> None:
        """
        Register a consumer to receive (features[18], window_end_ts) per window (recognizer/classifier)
        """
        self._features_sink = sink

    # Internals
    def _on_window_ready(self, window_rows: List[Tuple[float, ...]], window_ts: List[float]) -> None:
        """
        Build channel vectors, call processing, emit features.
        """
        self._windows_emitted += 1

        # Build 20 np.float32 vectors (length = window_size)
        # RIGHT accel (mg -> g -> m/s2)
        accX_R = (np.asarray([r[0] for r in window_rows], dtype=np.float32) / 1000.0) * G_TO_MPS2
        accY_R = (np.asarray([r[1] for r in window_rows], dtype=np.float32) / 1000.0) * G_TO_MPS2
        accZ_R = (np.asarray([r[2] for r in window_rows], dtype=np.float32) / 1000.0) * G_TO_MPS2

        # RIGHT gyro (dps)
        gyrX_R = np.asarray([r[3] for r in window_rows], dtype=np.float32)
        gyrY_R = np.asarray([r[4] for r in window_rows], dtype=np.float32)
        gyrZ_R = np.asarray([r[5] for r in window_rows], dtype=np.float32)

        # RIGHT quaternion (raw scaled by x10000; processing re-scales internally)
        quatRW_x = np.asarray([r[6]  for r in window_rows], dtype=np.float32)
        quatRW_y = np.asarray([r[7]  for r in window_rows], dtype=np.float32)
        quatRW_z = np.asarray([r[8]  for r in window_rows], dtype=np.float32)
        quatRW_w = np.asarray([r[9]  for r in window_rows], dtype=np.float32)

        # LEFT accel (mg -> g -> m/s2)
        accX_L = (np.asarray([r[10] for r in window_rows], dtype=np.float32) / 1000.0) * G_TO_MPS2
        accY_L = (np.asarray([r[11] for r in window_rows], dtype=np.float32) / 1000.0) * G_TO_MPS2
        accZ_L = (np.asarray([r[12] for r in window_rows], dtype=np.float32) / 1000.0) * G_TO_MPS2

        # LEFT gyro
        gyrX_L = np.asarray([r[13] for r in window_rows], dtype=np.float32)
        gyrY_L = np.asarray([r[14] for r in window_rows], dtype=np.float32)
        gyrZ_L = np.asarray([r[15] for r in window_rows], dtype=np.float32)

        # LEFT quaternion
        quatLW_x = np.asarray([r[16] for r in window_rows], dtype=np.float32)
        quatLW_y = np.asarray([r[17] for r in window_rows], dtype=np.float32)
        quatLW_z = np.asarray([r[18] for r in window_rows], dtype=np.float32)
        quatLW_w = np.asarray([r[19] for r in window_rows], dtype=np.float32)

        # SWAP X-Y and FLIP Z (ONLY FOR QUATERNIONS)
        # RIGHT
        quatRW_x, quatRW_y, quatRW_z, quatRW_w = self._align_xyzw_raw(quatRW_x, quatRW_y, quatRW_z, quatRW_w, apply=True)
        # LEFT
        quatLW_x, quatLW_y, quatLW_z, quatLW_w = self._align_xyzw_raw(quatLW_x, quatLW_y, quatLW_z, quatLW_w, apply=True)

        # Skip first window entirely for warmup
        if not self._calibrated and self._windows_emitted == 1:
            log_system("[DataBuffer] Skipping window #1 for data stabilization. Next window will calibrate")
            return

        # Call C processing
        try:
            if self._debug_print_buffer:
                log_system("[DataBuffer] [DEBUG] Pre-processing inputs: "
                            f"{accX_R}, {accY_R}, {accZ_R}, {gyrX_R}, {gyrY_R}, {gyrZ_R}, "
                            f"{accX_L}, {accY_L}, {accZ_L}, {gyrX_L}, {gyrY_L}, {gyrZ_L}, "
                            f"{quatRW_x}, {quatRW_y}, {quatRW_z}, {quatRW_w} ,"
                            f"{quatLW_x}, {quatLW_y}, {quatLW_z}, {quatLW_w} ,")

            features = process_data_wrists_quat(
                accX_R, accY_R, accZ_R, gyrX_R, gyrY_R, gyrZ_R,
                accX_L, accY_L, accZ_L, gyrX_L, gyrY_L, gyrZ_L,
                quatRW_x, quatRW_y, quatRW_z, quatRW_w,
                quatLW_x, quatLW_y, quatLW_z, quatLW_w
            )
            if not self._calibrated:
                self._calibrated = True
                log_system(f"[DataBuffer] Second window used for calibration (features discarded)")
                return

            if self._debug_print_features:
                log_system(f"[DataBuffer] [DEBUG] Processed outputs: \n " +
                           ", ".join(f"{x:.4f}" for x in features))

            # Ensure dtype/shape
            features = np.asarray(features, dtype=np.float32).reshape(-1)
        except Exception as e:
            log_system(f"[DataBuffer] process_data_wrists_quat error: {type(e).__name__}: {e}", level="ERROR")
            return

        window_end_ts = float(window_ts[-1]) if window_ts else 0.0

        log_system(f"[DataBuffer] window #{self._windows_emitted} processed")

        # Emit to subscriber (recognizer)
        if self._features_sink is not None:
            try:
                self._features_sink(features, window_end_ts)
            except Exception as e:
                log_system(f"[DataBuffer] features sink error: {type(e).__name__}: {e}", level="ERROR")

    # Calibration helper
    def is_calibrated(self) -> bool:
        """True after the one-time calibration window has been executed."""
        return self._calibrated

    # Hamilton product for elementwise arrays (scalar-first [w,x,y,z])
    @staticmethod
    def _qmul_wxyz( a_w, a_x, a_y, a_z, b_w, b_x, b_y, b_z):
        w = a_w * b_w - a_x * b_x - a_y * b_y - a_z * b_z
        x = a_w * b_x + a_x * b_w + a_y * b_z - a_z * b_y
        y = a_w * b_y - a_x * b_z + a_y * b_w + a_z * b_x
        z = a_w * b_z + a_x * b_y - a_y * b_x + a_z * b_w
        return w, x, y, z

    # Apply body-frame alignment (swap X↔Y, flip Z) to raw xyzw arrays (×10000).
    # Set apply=False to bypass (keeps ABI identical).
    def _align_xyzw_raw(self, quat_x, quat_y, quat_z, quat_w, apply=True):
        if not apply:
            return quat_x, quat_y, quat_z, quat_w

        # 1) raw -> unit, scalar-first
        w = quat_w.astype(np.float32).copy()
        x = quat_x.astype(np.float32).copy()
        y = quat_y.astype(np.float32).copy()
        z = quat_z.astype(np.float32).copy()

        n = np.sqrt(w * w + x * x + y * y + z * z)
        n[n == 0] = 1.0
        w /= n
        x /= n
        y /= n
        z /= n

        # 2) body-frame change: q_target = q_source ⊗ conj(q_align)
        #    For swap X<->Y & flip Z: q_align = [0, +√½, +√½, 0]  => conj() = [0, -√½, -√½, 0]
        c = np.float32(np.sqrt(0.5))
        qa_w, qa_x, qa_y, qa_z = np.float32(0.0), -c, -c, np.float32(0.0)
        w2, x2, y2, z2 = self._qmul_wxyz(w, x, y, z, qa_w, qa_x, qa_y, qa_z)

        # 3) renormalize, back to raw xyzw
        n2 = np.sqrt(w2 * w2 + x2 * x2 + y2 * y2 + z2 * z2)
        n2[n2 == 0] = 1.0
        w2 /= n2
        x2 /= n2
        y2 /= n2
        z2 /= n2

        scale = np.float32(10000.0)
        return (x2 * scale).astype(np.float32), (y2 * scale).astype(np.float32), \
            (z2 * scale).astype(np.float32), (w2 * scale).astype(np.float32)
