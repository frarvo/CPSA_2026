# event_dispatcher.py
# Dispatches recognized sensor events to the activation policy
# and triggers actions through the ActuatorManager
#
# Author: Francesco Urru
# Repository: https://github.com/frarvo/CPSA_2026
# License: MIT

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


class EventDispatcher:
    """
    Creates a thread that consumes event queue and dispatches actions via activation policy.

    Important behavior:
        - Long-running video gates poll the event queue while active.
        - If a newer tag arrives while YOLO or MoveNet is running, the active video
          thread is deactivated and the gate exits.
        - This mirrors the behavior of yolo_movenet_test.py, where pressing 0 can
          interrupt the active model immediately.
    """

    def __init__(self, actuator_manager, policy, yolo_thread=None, movenet_thread=None):
        self.actuator_manager = actuator_manager
        self.policy = policy
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._process_events, daemon=True)
        self._last_tag = None
        self._last_actuation_time = None

        self._latest_tag_lock = threading.Lock()
        self._latest_tag = None
        self._latest_event = None

        self.yolo_thread = yolo_thread
        self.movenet_thread = movenet_thread

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

    def _tag_changed_during_video_gate(self, expected_tag):
        latest_tag = self._get_latest_tag()
        return latest_tag is not None and latest_tag != expected_tag

    def _poll_pending_tag_change(self):
        """
        Drain pending sensor events while a video gate is running.

        The dispatcher normally cannot read new events while it is blocked inside
        YOLO/MoveNet confirmation. This method lets the video gate observe the
        newest tag and interrupt itself if the tag changed.

        This intentionally keeps only the latest queued event during a video gate.
        For this application, the video threads are controlled by current tag state,
        not by every intermediate duplicate event.
        """
        q = get_event_queue()
        latest_event = None
        latest_tag = None

        while True:
            try:
                event = q.get_nowait()
            except queue.Empty:
                break

            try:
                raw_tag = event.get("stereotipy_tag", "")

                try:
                    tag = int(raw_tag)
                except Exception:
                    tag = None

                latest_event = event
                latest_tag = tag

            finally:
                try:
                    q.task_done()
                except Exception:
                    pass

        if latest_event is not None:
            self._set_latest_tag(latest_tag, latest_event)
            log_system(
                f"[Dispatcher] Pending event observed during video gate: tag={latest_tag}",
                level="INFO",
            )

        return latest_tag

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

    def _run_yolo_person_gate(self, expected_tag, timeout_sec=30.0):
        if self.yolo_thread is None:
            log_system(
                "[Dispatcher] No YOLO thread configured. Person gate bypassed.",
                level="WARNING",
            )
            return True

        log_system("[Dispatcher] Starting YOLO person gate.", level="INFO")

        if self.movenet_thread and self.movenet_thread.is_active():
            self.movenet_thread.deactivate()
            self._wait_thread_idle(self.movenet_thread, "MoveNet")

        self.yolo_thread.activate()

        start = time.monotonic()

        while not self._stop_event.is_set():
            self._poll_pending_tag_change()

            if self._tag_changed_during_video_gate(expected_tag):
                log_system(
                    f"[Dispatcher] YOLO gate interrupted: tag changed from {expected_tag} "
                    f"to {self._get_latest_tag()}",
                    level="INFO",
                )
                self.yolo_thread.deactivate()
                self._wait_thread_idle(self.yolo_thread, "YOLO")
                return False

            if not self.yolo_thread.is_active() and getattr(self.yolo_thread, "phase", None) == "idle":
                log_system(
                    "[Dispatcher] YOLO became idle before person gate passed.",
                    level="INFO",
                )
                return False

            person_detected, _ = self.yolo_thread.get_latest_result()

            if person_detected is True:
                log_system("[Dispatcher] YOLO person gate passed.", level="INFO")
                return True

            if time.monotonic() - start >= timeout_sec:
                log_system(
                    "[Dispatcher] YOLO person gate failed: no person detected.",
                    level="INFO",
                )
                self.yolo_thread.deactivate()
                self._wait_thread_idle(self.yolo_thread, "YOLO")
                return False

            time.sleep(0.05)

        self.yolo_thread.deactivate()
        self._wait_thread_idle(self.yolo_thread, "YOLO")
        return False

    def _run_movenet_confirmation(self, expected_tag, timeout_sec=30.0):
        if self.movenet_thread is None:
            log_system(
                "[Dispatcher] No MoveNet thread configured. MoveNet confirmation bypassed.",
                level="WARNING",
            )
            return True

        log_system("[Dispatcher] Starting MoveNet confirmation.", level="INFO")

        if self.yolo_thread and self.yolo_thread.is_active():
            self.yolo_thread.deactivate()
            self._wait_thread_idle(self.yolo_thread, "YOLO")

        self.movenet_thread.activate()

        start = time.monotonic()

        while not self._stop_event.is_set():
            self._poll_pending_tag_change()

            if self._tag_changed_during_video_gate(expected_tag):
                log_system(
                    f"[Dispatcher] MoveNet confirmation interrupted: tag changed from {expected_tag} "
                    f"to {self._get_latest_tag()}",
                    level="INFO",
                )
                self.movenet_thread.deactivate()
                self._wait_thread_idle(self.movenet_thread, "MoveNet")
                return False

            if not self.movenet_thread.is_active() and getattr(self.movenet_thread, "phase", None) == "idle":
                log_system(
                    "[Dispatcher] MoveNet became idle before confirmation passed.",
                    level="INFO",
                )
                return False

            keypoints, _ = self.movenet_thread.get_latest_result()

            if keypoints is not None:
                log_system("[Dispatcher] MoveNet confirmation passed.", level="INFO")
                return True

            if time.monotonic() - start >= timeout_sec:
                log_system("[Dispatcher] MoveNet confirmation timeout.", level="INFO")
                self.movenet_thread.deactivate()
                self._wait_thread_idle(self.movenet_thread, "MoveNet")
                return False

            time.sleep(0.05)

        self.movenet_thread.deactivate()
        self._wait_thread_idle(self.movenet_thread, "MoveNet")
        return False

    def _run_video_gate_for_new_tag(self, tag):
        if tag == 1:
            return self._run_yolo_person_gate(
                expected_tag=tag,
                timeout_sec=30.0,
            )

        if tag == 2:
            yolo_ok = self._run_yolo_person_gate(
                expected_tag=tag,
                timeout_sec=30.0,
            )

            if not yolo_ok:
                return False

            return self._run_movenet_confirmation(
                expected_tag=tag,
                timeout_sec=30.0,
            )

        self._stop_video_threads()
        return True

    def _check_video_for_same_tag_retry(self, tag):
        if tag == 1:
            if self.yolo_thread is None:
                return True

            person_detected, _ = self.yolo_thread.get_latest_result()
            return person_detected is True

        if tag == 2:
            if self.movenet_thread is None:
                return True

            keypoints, _ = self.movenet_thread.get_latest_result()
            return keypoints is not None

        return True

    def _trigger_policy_action(self, event):
        result = self.policy.handle(event)

        if not result:
            log_system("[Dispatcher] Policy returned no action.")
            return None

        self.actuator_manager.trigger(
            actuator_id=result["actuator_id"],
            action_type="stereotipy_event",
            **result["params"],
        )

        return result

    def _process_events(self):
        q = get_event_queue()

        while not self._stop_event.is_set():
            try:
                event = q.get(timeout=0.5)
            except queue.Empty:
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
                    f"[Dispatcher] Event received: raw_tag={raw_tag}, tag={tag}, "
                    f"last_tag={self._last_tag}",
                    level="INFO",
                )

                if tag != self._last_tag:
                    actuations = []

                    video_ok = self._run_video_gate_for_new_tag(tag)

                    if video_ok:
                        try:
                            result = self._trigger_policy_action(event)
                        except Exception as e:
                            log_system(f"[Dispatcher] Trigger error: {e}", level="ERROR")
                            result = None
                    else:
                        result = None
                        log_system("[Dispatcher] Actuation blocked by video gate.")

                    if result:
                        actuations = [
                            {
                                "target": result["actuator_id"],
                                "params": result["params"],
                            }
                        ]
                        self._last_actuation_time = now_time
                    else:
                        self._last_actuation_time = None

                    log_event(
                        timestamp=event.get("timestamp"),
                        feature_type="imu",
                        event=label,
                        actuations=actuations,
                        source=event.get("source", "dual_wrist"),
                    )

                    # If the video gate was interrupted by a newer tag, keep the
                    # dispatcher's last tag aligned with the newest observed state.
                    self._last_tag = self._get_latest_tag()

                else:
                    if tag in (1, 2):
                        should_retry = (
                            self._last_actuation_time is None
                            or (now_time - self._last_actuation_time) >= ACTUATION_COOLDOWN
                        )

                        if should_retry:
                            video_ok = self._check_video_for_same_tag_retry(tag)

                            if video_ok:
                                try:
                                    result = self._trigger_policy_action(event)
                                except Exception as e:
                                    log_system(
                                        f"[Dispatcher] Trigger retry error: {e}",
                                        level="ERROR",
                                    )
                                    result = None
                            else:
                                result = None
                                log_system(
                                    "[Dispatcher] Actuation retry blocked by video gate."
                                )
                                self._last_actuation_time = now_time

                            if result:
                                self._last_actuation_time = now_time

            except Exception as e:
                log_system(f"[Dispatcher] Dispatch error: {e}", level="ERROR")

            finally:
                try:
                    q.task_done()
                except Exception:
                    pass
