# lock.py
# Global lock for bluetooth scan safety
#
# Author: Francesco Urru
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

import threading

device_scan_lock = threading.Lock()
device_connection_lock = threading.Lock()
device_reconnection_lock = threading.RLock()

logging_lock = threading.Lock()
