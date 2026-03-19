# data_processing_wrapper_quat.py
# Defines the python interface for the data processing chain functions
#
# Author: Francesco Urru
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

import ctypes as ct
import numpy as np
import os
from numpy.ctypeslib import ndpointer
from utils.config import get_buffer_config

# Load data processing library
lib_dir = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(lib_dir, "libProcessDataWristsQuat.so")
lib = ct.CDLL(LIB_PATH)

# Define constants
N = get_buffer_config().get("window_size")  # Input channel size
FEAT = 18   # Output feature vector length

# Define data types
Float150 = ndpointer(dtype=np.float32, shape=(N,), flags=("C_CONTIGUOUS",))
Float18  = ndpointer(dtype=np.float32, shape=(FEAT,), flags=("C_CONTIGUOUS",))


# Define function interface
# Inputs
lib.ProcessDataWristsQuat.argtypes = [
    # RIGHT acc_x, acc_y, acc_z, gyr_x, gyr_y, gyr_z
    Float150, Float150, Float150, Float150, Float150, Float150,
    # LEFT acc_x, acc_y, acc_z, gyr_x, gyr_y, gyr_z
    Float150, Float150, Float150, Float150, Float150, Float150,
    # RIGHT quaternions x, y, z, w
    Float150, Float150, Float150, Float150,
    # LEFT quaternions x, y, z, w
    Float150, Float150, Float150, Float150,
    # OUTPUT
    Float18
]
# Outputs
lib.ProcessDataWristsQuat.restype = None

# Try to use init in the library header. If stripped just skip
try:
    lib.ProcessDataWristsQuat_init.restype = None
except AttributeError:
    pass

def _as_f32_150(x):
    """
    Ensure a size N float32 array
    """
    a = np.asarray(x, dtype=np.float32).reshape(-1)
    if a.size != N:
        raise ValueError(f"Expected lenght {N}, got {a.size}")
    if not a.flags.c_contiguous:
        a = np.ascontiguousarray(a, dtype=np.float32)
    elif a.dtype != np.float32:
        a = a.astype(np.float32, copy=False)
    if not a.flags.writeable:
        a = a.copy()
    return a

def initialize():
    """
    Calls ProcessDataWristsQuat_init if available
    """
    f = getattr(lib, "ProcessDataWristsQuat_initialize", None) or getattr(lib, "ProcessDataWristsQuat_init", None)
    if f:
        f()


# Wrapper Python
def process_data_wrists_quat(
    accX_R, accY_R, accZ_R, gyrX_R, gyrY_R, gyrZ_R,
    accX_L, accY_L, accZ_L, gyrX_L, gyrY_L, gyrZ_L,
    quatRW_x, quatRW_y, quatRW_z, quatRW_w,
    quatLW_x, quatLW_y, quatLW_z, quatLW_w,
) -> np.ndarray:
    """
    Call the C library for data processing and return imuFeatures[18] as float32.
    All vector inputs are length 150 float32.
    Arguments order MUST match API order.
    """
    ins = [ accX_R, accY_R, accZ_R, gyrX_R, gyrY_R, gyrZ_R,
            accX_L, accY_L, accZ_L, gyrX_L, gyrY_L, gyrZ_L,
            quatRW_x, quatRW_y, quatRW_z, quatRW_w,
            quatLW_x, quatLW_y, quatLW_z, quatLW_w,
            ]
    arrs = [_as_f32_150(v) for v in ins]
    out = np.empty(FEAT, dtype=np.float32)

    # Call C API
    lib.ProcessDataWristsQuat(*arrs, out)

    return out