# predict_models_wrapper_quat.py
# Defines the python interface for stereotipy prediction model
#
# Author: Francesco Urru
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

import ctypes as ct
import numpy as np
import os
from numpy.ctypeslib import ndpointer


# Load classifier library
lib_dir = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(lib_dir, "libPredictPericolosaWristsQuat.so")
lib = ct.CDLL(LIB_PATH)

# Define constants
FEAT = 18   # Input features

# Define data types
Float18  = ndpointer(dtype=np.float32, shape=(FEAT,), flags=("C_CONTIGUOUS",))

# Define function interface
# Inputs
lib.Predict_Pericolosa_Wrists_Quat.argtypes = [Float18]
# Outputs
lib.Predict_Pericolosa_Wrists_Quat.restype = ct.c_ubyte

# Optional init
try:
    lib.c_Predict_Pericolosa_Wrists_Qua.restype = None
    _HAS_INIT = True
except AttributeError:
    _HAS_INIT = False

def _as_f32_150(x):
    """
    Ensure a size 18 float32 array
    """
    a = np.asarray(x, dtype=np.float32).reshape(-1)
    if a.size != FEAT:
        raise ValueError(f"Expected lenght {FEAT}, got {a.size}")
    a = np.ascontiguousarray(a, dtype=np.float32)
    return a

def initialize():
    if _HAS_INIT:
        lib.c_Predict_Pericolosa_Wrists_Qua()

def predict_pericolosa_wrists_quat(x) -> int:
    """
    X: 18 length array float32
    returns an int label for detected stereotipy (1, 2, 3)
    """
    a = _as_f32_150(x)
    return int(lib.Predict_Pericolosa_Wrists_Quat(a))