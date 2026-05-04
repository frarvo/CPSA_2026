# classifiers/stereotipy_classifier.py
# Classifier for dual-wrist data (processed features -> classification -> event)
#
# Author: Francesco Urru
# Github: https://github.com/frarvo
# Repository: https://github.com/frarvo/CPSA_2026
# License: MIT

import uuid
from datetime import datetime
import numpy as np

from utils.logger import log_system, log_event
from utils.event_queue import enqueue_drop_oldest, get_event_queue

# Import model wrapper
from IMU_pipeline.classifiers.stereotipy_classifier.predict_models_wrapper_quat import (
    predict_pericolosa_wrists_quat, initialize
)


class StereotipyClassifier:
    """
    Interface for stereotipy classification.
    Consumes 18-feature vector (float32) from processing pipeline,
    runs model, and enqueues recognition events for actuation.
    """

    def __init__(self, source: str = "dual_wrist"):
        self.source = source
        self.q = get_event_queue()
        # Initialize classifier
        initialize()

    # Sink for buffer callback to processing
    def recognize(self, features: np.ndarray, ts: float):
        """
        Recognize from processed features. Entry point from buffer
        Args:
            features (np.ndarray): shape (18,), dtype float32
            ts: timestamp of last buffer row
        """
        try:
            feats = np.asarray(features, dtype=np.float32).reshape(-1)
        except Exception as e:
            log_system(f"[Classifier] Bad feature vector: {type(e).__name__}: {e}", level="ERROR")
            return None
        try:
            event = {
                "id": uuid.uuid4().hex,
                "timestamp": datetime.now().isoformat(),
                "window_ts": float(ts) if ts is not None else None,
                "source": self.source,
                "features": features.tolist(),
                "stereotipy_tag": str(predict_pericolosa_wrists_quat(feats))
            }
        except Exception as e:
            log_system(f"[Classifier] Error: {type(e).__name__}: {e}", level="ERROR")
            return None

        dropped, dropped_item = enqueue_drop_oldest(self.q, event, kind="imu")
        if dropped:
            log_system("[Classifier] Oldest event dropped (queue full)", level="WARNING")
            try:
                ev = dropped_item or {}
                log_event(
                    timestamp=ev.get("timestamp", event["timestamp"]),
                    feature_type=ev.get("type", "imu"),
                    event=ev.get("stereotipy_tag", "UNKNOWN"),
                    actuations=[{"target": "DROPPED", "params":{"reason":"queue_full"}}],
                    source=ev.get("source", self.source),
                )
            except Exception:
                pass

        #log_system(f"[Classifier] Event enqueued: {event}")
        return event