# event_dispatcher.py
# Dispatches recognized sensor events to the activation policy
# and triggers actions through the ActuatorManager

import queue
import threading
import time

from utils.event_queue import get_event_queue
from utils.logger import log_system, log_event


LABELS = {
    0: "NO_CLASS",
    1: "NON_DANGEROUS",
    2: "DANGEROUS",
    3: "NON_STEREOTIPY",
}

ACTUATION_COOLDOWN = 5
# When YOLO is reacquiring, only switch back to MoveNet if the latest YOLO bbox is at most YOLO_REFRESH_MAX_AGE_SEC old.
YOLO_REFRESH_MAX_AGE_SEC = 1.0
# YOLO_REACQUIRE_MIN_INTERVAL_SEC: Do not request YOLO reacquisition more often than once every YOLO_REACQUIRE_MIN_INTERVAL_SEC 
YOLO_REACQUIRE_MIN_INTERVAL_SEC = 2.0
# YOLO_REACQUIRE_TIMEOUT_SEC: If YOLO cannot reacquire a person after YOLO_REACQUIRE_TIMEOUT_SEC, stop the video stage.
YOLO_REACQUIRE_TIMEOUT_SEC = 5.0

class EventDispatcher:
    """
    Consumes IMU classifier events and dispatches actions via activation policy.

    Video behavior:
        - Video state follows the latest IMU tag.
        - Video activation is non-blocking.
        - For tag=1: YOLO stays active while tag remains 1.
        - For tag=2: YOLO runs first; after person detection, YOLO stops and MoveNet starts.
        - YOLO and MoveNet are never active together.
        - For tag=0 or tag=3: all video threads stop.
    """

    def __init__(
            self,
            actuator_manager,
            policy,
            yolo_thread=None,
            movenet_thread=None,
            roi_state=None,
        ):
        self.actuator_manager = actuator_manager
        self.policy = policy
        self.roi_state = roi_state

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._process_events, daemon=True)

        self._last_tag = None
        self._last_actuation_time = None

        self._latest_tag_lock = threading.Lock()
        self._latest_tag = None
        self._latest_event = None

        self.yolo_thread = yolo_thread
        self.movenet_thread = movenet_thread

        # None | "yolo_tag1" | "yolo_tag2" | "movenet_tag2"
        self._video_stage = None

        self._last_yolo_reacquire_request_ts = None
        self._yolo_tag2_started_ts = None

    def start(self):
        self._thread.start()
        log_system("[Dispatcher] Started.")

    def stop(self):
        self._stop_event.set()
        self._stop_video_threads()

        if self._thread.is_alive():
            self._thread.join()

        log_system("[Dispatcher] Stopped.")

    def _set_latest_tag(self, tag, event):
        with self._latest_tag_lock:
            self._latest_tag = tag
            self._latest_event = event

    def _get_latest_tag(self):
        with self._latest_tag_lock:
            return self._latest_tag

    def _wait_thread_idle(self, thread, name, timeout_sec=5.0):
        if thread is None:
            return True

        start = time.monotonic()

        while not self._stop_event.is_set():
            if getattr(thread, "phase", None) == "idle":
                return True

            if time.monotonic() - start >= timeout_sec:
                log_system(
                    f"[Dispatcher] Timeout waiting for {name} to become idle. "
                    f"Current phase={getattr(thread, 'phase', 'unknown')}",
                    level="WARNING",
                )
                return False

            time.sleep(0.05)

        return False

    def _stop_video_threads(self):
        if self.yolo_thread and self.yolo_thread.is_active():
            log_system("[Dispatcher] Stopping YOLO thread.", level="INFO")
            self.yolo_thread.deactivate()
            self._wait_thread_idle(self.yolo_thread, "YOLO")

        if self.movenet_thread and self.movenet_thread.is_active():
            log_system("[Dispatcher] Stopping MoveNet thread.", level="INFO")
            self.movenet_thread.deactivate()
            self._wait_thread_idle(self.movenet_thread, "MoveNet")

        self._video_stage = None
        self._yolo_tag2_started_ts = None

        if self.roi_state is not None:
            self.roi_state.clear()

    def _activate_yolo(self, stage):
        if self.movenet_thread and self.movenet_thread.is_active():
            log_system("[Dispatcher] Stopping MoveNet before activating YOLO.", level="INFO")
            self.movenet_thread.deactivate()
            self._wait_thread_idle(self.movenet_thread, "MoveNet")

        if self.yolo_thread is None:
            log_system("[Dispatcher] YOLO thread not configured.", level="WARNING")
            self._video_stage = None
            return

        previous_stage = self._video_stage

        if not self.yolo_thread.is_active():
            log_system(f"[Dispatcher] Activating YOLO. stage={stage}", level="INFO")
            self.yolo_thread.activate()

        self._video_stage = stage

        if stage == "yolo_tag2" and previous_stage != "yolo_tag2":
            self._yolo_tag2_started_ts = time.monotonic()

    def _activate_movenet(self, stage):
        if self.yolo_thread and self.yolo_thread.is_active():
            log_system("[Dispatcher] Stopping YOLO before activating MoveNet.", level="INFO")
            self.yolo_thread.deactivate()
            self._wait_thread_idle(self.yolo_thread, "YOLO")

        if self.movenet_thread is None:
            log_system("[Dispatcher] MoveNet thread not configured.", level="WARNING")
            self._video_stage = None
            return

        if not self.movenet_thread.is_active():
            log_system(f"[Dispatcher] Activating MoveNet. stage={stage}", level="INFO")
            self.movenet_thread.activate()

        self._video_stage = stage

        if stage == "movenet_tag2":
            self._yolo_tag2_started_ts = None

    def _apply_video_state_for_tag(self, tag):
        """
        Non-blocking video state update.

        tag 0: stop video
        tag 1: YOLO only while tag remains 1
        tag 2: YOLO first; when person detected, switch to MoveNet
        tag 3: stop video
        """

        if tag == 1:
            if self._video_stage != "yolo_tag1":
                self._activate_yolo("yolo_tag1")
            return

        if tag == 2:
            if self._video_stage is None or self._video_stage == "yolo_tag1":
                self._activate_yolo("yolo_tag2")
                return

            if self._video_stage == "yolo_tag2":
                if self.yolo_thread is None:
                    return

                person_bbox, person_conf, person_bbox_ts = (
                    self.yolo_thread.get_latest_person_bbox()
                )
                bbox_is_fresh = (
                    person_bbox is not None
                    and person_bbox_ts is not None
                    and (time.monotonic() - person_bbox_ts) <= YOLO_REFRESH_MAX_AGE_SEC
                )

                if bbox_is_fresh:
                    log_system(
                        f"[Dispatcher] Fresh YOLO person ROI acquired for tag=2. "
                        f"bbox={person_bbox}, conf={person_conf:.2f}. "
                        f"Switching to MoveNet.",
                        level="INFO",
                    )
                    self._activate_movenet("movenet_tag2")

                    return

                if self._yolo_tag2_started_ts is not None:
                    yolo_elapsed = time.monotonic() - self._yolo_tag2_started_ts

                    if yolo_elapsed >= YOLO_REACQUIRE_TIMEOUT_SEC:
                        log_system(
                            f"[Dispatcher] YOLO tag=2 reacquisition timed out after "
                            f"{yolo_elapsed:.1f}s. Stopping video threads.",
                            level="WARNING",
                        )
                        self._stop_video_threads()

                return

            if self._video_stage == "movenet_tag2":
                if self.movenet_thread is None:
                    return

                if self.roi_state is not None and self.roi_state.needs_reacquire():
                    now = time.monotonic()

                    if (
                        self._last_yolo_reacquire_request_ts is not None
                        and now - self._last_yolo_reacquire_request_ts < YOLO_REACQUIRE_MIN_INTERVAL_SEC
                    ):
                        return

                    self._last_yolo_reacquire_request_ts = now

                    log_system(
                        "[Dispatcher] MoveNet requested ROI reacquisition. Switching back to YOLO.",
                        level="INFO",
                    )
                    self._activate_yolo("yolo_tag2")
                    return

                if not self.movenet_thread.is_active():
                    self._activate_movenet("movenet_tag2")

                return

        self._stop_video_threads()

    def _trigger_policy_action(self, event):
        log_system(
            f"[Dispatcher POLICY IN] tag={event.get('stereotipy_tag')} "
            f"source={event.get('source')}",
            level="INFO",
        )

        result = self.policy.handle(event)

        log_system(
            f"[Dispatcher POLICY OUT] result={result}",
            level="INFO",
        )

        if not result:
            log_system("[Dispatcher] Policy returned no action.")
            return None

        self.actuator_manager.trigger(
            actuator_id=result["actuator_id"],
            action_type="stereotipy_event",
            **result["params"],
        )

        return result

    def _should_trigger_policy(self, tag, now_time):
        if tag not in (1, 2):
            return False

        return (
            self._last_actuation_time is None
            or (now_time - self._last_actuation_time) >= ACTUATION_COOLDOWN
        )

    def _process_policy_for_event(self, event, tag, now_time):
        if not self._should_trigger_policy(tag, now_time):
            return None

        try:
            result = self._trigger_policy_action(event)
        except Exception as e:
            log_system(f"[Dispatcher] Trigger error: {e}", level="ERROR")
            return None

        if result:
            self._last_actuation_time = now_time

        return result

    def _process_events(self):
        q = get_event_queue()

        while not self._stop_event.is_set():
            try:
                event = q.get(timeout=0.5)
            except queue.Empty:
                latest_tag = self._get_latest_tag()

                if latest_tag is not None:
                    self._apply_video_state_for_tag(latest_tag)

                continue

            try:
                raw_tag = event.get("stereotipy_tag", "")

                try:
                    tag = int(raw_tag)
                except Exception:
                    tag = None

                label = LABELS.get(tag, str(raw_tag))
                now_time = time.monotonic()

                self._set_latest_tag(tag, event)

                log_system(
                    f"[Dispatcher IN] raw_tag={raw_tag}, tag={tag}, "
                    f"label={label}, last_tag={self._last_tag}, "
                    f"video_stage={self._video_stage}, "
                    f"queue_size={q.qsize() if hasattr(q, 'qsize') else 'unknown'}",
                    level="INFO",
                )

                tag_changed = tag != self._last_tag

                if tag_changed:
                    log_system(
                        f"[Dispatcher] Tag changed: {self._last_tag} -> {tag} ({label})",
                        level="INFO",
                    )

                    self._last_tag = tag
                    self._last_actuation_time = None

                self._apply_video_state_for_tag(tag)

                result = self._process_policy_for_event(event, tag, now_time)

                actuations = []
                if result:
                    actuations = [
                        {
                            "target": result["actuator_id"],
                            "params": result["params"],
                        }
                    ]

                if tag_changed:
                    log_event(
                        timestamp=event.get("timestamp"),
                        feature_type="imu",
                        event=label,
                        actuations=actuations,
                        source=event.get("source", "dual_wrist"),
                    )

            except Exception as e:
                log_system(f"[Dispatcher] Dispatch error: {e}", level="ERROR")

            finally:
                try:
                    q.task_done()
                except Exception:
                    pass