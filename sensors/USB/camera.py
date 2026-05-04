import cv2
import threading
import time

from VIDEO_pipeline.yolo_detection import YoloDetectionPipeline
from utils.logger import log_system


class YoloDpuThread(threading.Thread):
    def __init__(self, device_id: str = "camera0", camera_index: int = 0):
        super().__init__(daemon=True)

        self.device_id = device_id
        self.camera_index = camera_index

        self.stop_event = threading.Event()
        self.active_event = threading.Event()

        self.cap = None
        self.pipeline = None

        self.result_lock = threading.Lock()
        self.latest_result = None
        self.latest_result_ts = None

        self.no_person_timeout_sec = 5.0
        self._last_person_seen_ts = None

    def activate(self):
        self.active_event.set()

    def deactivate(self):
        self.active_event.clear()
        self._last_person_seen_ts = None

        with self.result_lock:
            self.latest_result = None
            self.latest_result_ts = None

    def is_active(self):
        return self.active_event.is_set()

    def get_latest_result(self):
        with self.result_lock:
            return self.latest_result, self.latest_result_ts

    def run(self):
        self.pipeline = YoloDetectionPipeline()

        while not self.stop_event.is_set():
            if not self.active_event.wait(timeout=0.5):
                continue

            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                log_system("[YoloDpuThread] Webcam not found", level="ERROR")
                self.active_event.clear()
                continue

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            self._last_person_seen_ts = time.monotonic()

            while self.active_event.is_set() and not self.stop_event.is_set():
                ret, frame = self.cap.read()
                if not ret:
                    break

                frame, person_detected = self.pipeline.process_frame(frame)

                now = time.monotonic()

                if person_detected:
                    self._last_person_seen_ts = now
                else:
                    if self._last_person_seen_ts is not None and \
                       (now - self._last_person_seen_ts) >= self.no_person_timeout_sec:
                        self.deactivate()
                        break

                with self.result_lock:
                    self.latest_result = person_detected
                    self.latest_result_ts = now

                cv2.imshow("YOLOv3 DPU", frame)
                cv2.waitKey(1)

            if self.cap:
                self.cap.release()
                self.cap = None

            cv2.destroyAllWindows()

        if self.pipeline:
            self.pipeline.close()
            self.pipeline = None

    def stop(self):
        self.stop_event.set()
        self.active_event.set()

        if self.is_alive():
            self.join()