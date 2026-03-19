# event_queue.py
# Centralized queues for sensor event dispatching
#
# Author: Francesco Urru
# GitHub: https://github.com/frarvo
# Repository: https://github.com/frarvo/STOPme
# License: MIT

from queue import Queue, Full, Empty
from typing import Optional, Tuple, Any
from utils.config import get_event_queue_size

MAX_Q_SIZE = get_event_queue_size()

# Shared queue (with limit to avoid stacking and losing real time)
_event_queue = Queue(maxsize=MAX_Q_SIZE)

# Counter for internal regulation (if an event is dropped when queue is full, duration would be wrong)
_dropped_counts = {"imu":0, "event":0}

def get_event_queue() -> Queue:
    """
    Returns the global queue for activity events.
    """
    return _event_queue

def enqueue_drop_oldest(q: Queue, item, kind:Optional[str] = None) -> Tuple[bool, Optional[Any]]:
    """
    Enque 'item'. If queue is full, drops the oldest item. Reduces latency
    Returns dropped flag and dropped item
    """
    try:
        q.put_nowait(item)
        return False, None
    except Full:
        # Queue is full, drop oldest, try new enqueue
        dropped_item = None
        try:
            dropped_item = q.get_nowait()
        except Empty:
            return False,None
        try:
            q.put_nowait(item)
        except Full:
            pass
        if kind:
            _dropped_counts[kind] = _dropped_counts.get(kind, 0) + 1
            return True,dropped_item

def get_drop_count(kind:str) -> int:
    """
    Returns number of dropped items
    """
    return _dropped_counts.get(kind,0)