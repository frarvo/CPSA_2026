import threading
import time

# YOLO alpha high: trust detector more, correct quickly.
YOLO_SMOOTH_ALPHA = 0.85
# MoveNet alpha lower: smooth noisy keypoint-derived ROI updates.
MOVENET_SMOOTH_ALPHA = 0.35


class PersonRoiState:
    """
    Thread-safe shared person ROI state.

    Coordinates are always full-frame xyxy:
        (x1, y1, x2, y2)

    Internally, the ROI is smoothed in cx, cy, w, h space.

    The state is intended to be:
        - written by YOLO when a person is detected
        - read by MoveNet for ROI-based cropping
        - updated by MoveNet from confident keypoints
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Latest raw bbox received from YOLO or MoveNet.
        self._raw_bbox_xyxy = None

        # Smoothed bbox returned to consumers.
        self._bbox_xyxy = None

        # Internal smoothed representation: cx, cy, w, h.
        self._smoothed_cxcywh = None

        self._confidence = 0.0
        self._timestamp = None
        self._source = None

        self._need_reacquire = True

    # -----------------------------------------------------
    # PUBLIC UPDATE API
    # -----------------------------------------------------

    def update_from_yolo(self, bbox_xyxy, confidence):
        """
        Update ROI using a YOLO person detection.

        YOLO is treated as a stronger correction source, so it uses
        a higher smoothing alpha.
        """
        self._update(
            bbox_xyxy=bbox_xyxy,
            confidence=confidence,
            source="yolo",
            alpha=YOLO_SMOOTH_ALPHA
        )

    def update_from_movenet(self, bbox_xyxy, confidence):
        """
        Update ROI using MoveNet keypoints.

        MoveNet keypoint-derived boxes are usually noisier frame-to-frame,
        so they use a lower smoothing alpha.
        """
        self._update(
            bbox_xyxy=bbox_xyxy,
            confidence=confidence,
            source="movenet",
            alpha=MOVENET_SMOOTH_ALPHA
        )

    # -----------------------------------------------------
    # INTERNAL HELPERS
    # -----------------------------------------------------

    @staticmethod
    def _xyxy_to_cxcywh(bbox_xyxy):
        x1, y1, x2, y2 = bbox_xyxy

        w = float(x2 - x1)
        h = float(y2 - y1)
        cx = float(x1) + 0.5 * w
        cy = float(y1) + 0.5 * h

        return cx, cy, w, h

    @staticmethod
    def _cxcywh_to_xyxy(cxcywh):
        cx, cy, w, h = cxcywh

        x1 = cx - 0.5 * w
        y1 = cy - 0.5 * h
        x2 = cx + 0.5 * w
        y2 = cy + 0.5 * h

        return (
            int(round(x1)),
            int(round(y1)),
            int(round(x2)),
            int(round(y2))
        )

    @staticmethod
    def _is_valid_bbox(bbox_xyxy):
        if bbox_xyxy is None:
            return False

        x1, y1, x2, y2 = bbox_xyxy

        return x2 > x1 and y2 > y1

    def _update(self, bbox_xyxy, confidence, source, alpha):
        if not self._is_valid_bbox(bbox_xyxy):
            return

        x1, y1, x2, y2 = bbox_xyxy

        raw_bbox = (
            int(x1),
            int(y1),
            int(x2),
            int(y2)
        )

        new_cxcywh = self._xyxy_to_cxcywh(raw_bbox)

        now = time.monotonic()

        with self._lock:
            if self._smoothed_cxcywh is None:
                smoothed = new_cxcywh
            else:
                old_cx, old_cy, old_w, old_h = self._smoothed_cxcywh
                new_cx, new_cy, new_w, new_h = new_cxcywh

                smoothed = (
                    alpha * new_cx + (1.0 - alpha) * old_cx,
                    alpha * new_cy + (1.0 - alpha) * old_cy,
                    alpha * new_w + (1.0 - alpha) * old_w,
                    alpha * new_h + (1.0 - alpha) * old_h,
                )

            smoothed_bbox = self._cxcywh_to_xyxy(smoothed)

            if not self._is_valid_bbox(smoothed_bbox):
                return

            self._raw_bbox_xyxy = raw_bbox
            self._bbox_xyxy = smoothed_bbox
            self._smoothed_cxcywh = smoothed
            self._confidence = float(confidence)
            self._timestamp = now
            self._source = source
            self._need_reacquire = False

    # -----------------------------------------------------
    # PUBLIC READ API
    # -----------------------------------------------------

    def get_snapshot(self):
        """
        Return the current ROI state without age filtering.

        Returns:
            dict with raw bbox, smoothed bbox, confidence, timestamp,
            source, and need_reacquire.
        """
        with self._lock:
            return {
                "bbox_xyxy": self._bbox_xyxy,
                "raw_bbox_xyxy": self._raw_bbox_xyxy,
                "confidence": self._confidence,
                "timestamp": self._timestamp,
                "source": self._source,
                "need_reacquire": self._need_reacquire,
            }

    def get_valid_roi(self, max_age_sec=None):
        """
        Return smoothed bbox if available and not stale.

        Args:
            max_age_sec:
                If None, no age filtering is applied.
                Otherwise, bbox is returned only if recent enough.

        Returns:
            Smoothed (x1, y1, x2, y2) or None.
        """
        with self._lock:
            if self._bbox_xyxy is None or self._timestamp is None:
                return None

            if self._need_reacquire:
                return None

            if max_age_sec is not None:
                age = time.monotonic() - self._timestamp
                if age > max_age_sec:
                    return None

            return self._bbox_xyxy

    def mark_reacquire(self):
        """
        Mark current ROI as unreliable.

        The smoothed bbox is intentionally kept in memory, but get_valid_roi()
        will stop returning it until a new update clears need_reacquire.
        """
        with self._lock:
            self._need_reacquire = True

    def needs_reacquire(self):
        """
        Return True if YOLO should reacquire the person ROI.
        """
        with self._lock:
            return self._need_reacquire

    def clear(self):
        """
        Clear the ROI completely.
        """
        with self._lock:
            self._raw_bbox_xyxy = None
            self._bbox_xyxy = None
            self._smoothed_cxcywh = None
            self._confidence = 0.0
            self._timestamp = None
            self._source = None
            self._need_reacquire = True