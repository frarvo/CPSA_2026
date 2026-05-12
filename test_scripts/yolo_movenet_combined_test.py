import time

from VIDEO_pipeline.YOLO.yolo_thread import YoloDpuThread
from VIDEO_pipeline.MOVENET.movenet_thread import MoveNetDpuThread

from utils.video_dashboard import VideoDashboard


dashboard = None


def dlog(message):
    global dashboard

    if dashboard is not None:
        dashboard.log(message)
    else:
        print(message)


def get_phase(thread):
    return getattr(thread, "phase", "unknown")


def is_idle_like(thread):
    return get_phase(thread) in {"idle", "stopped", "error"}


def render_dashboard(yolo, movenet):
    global dashboard

    if dashboard is not None:
        dashboard.render(yolo, movenet)


def read_key(delay_ms=1):
    global dashboard

    if dashboard is None:
        return -1

    key = dashboard.wait_key(delay_ms)

    if key is None:
        return -1

    return key & 0xFF


def wait_phase_ready(yolo, movenet, timeout_sec=20.0):
    """
    Wait until both model threads have finished loading their DPU runners.

    The threads start in/loading may stay in "loading" for a while.
    The test should not accept 1/2 triggers until both are idle.
    """
    start = time.monotonic()

    while True:
        yolo_phase = get_phase(yolo)
        movenet_phase = get_phase(movenet)

        if yolo_phase == "idle" and movenet_phase == "idle":
            return True

        if yolo_phase == "error" or movenet_phase == "error":
            dlog(
                "[TEST] Thread initialization failed. "
                f"YOLO phase={yolo_phase}, MoveNet phase={movenet_phase}"
            )
            return False

        if time.monotonic() - start >= timeout_sec:
            dlog(
                "[TEST] Timeout waiting for model threads to become ready. "
                f"YOLO phase={yolo_phase}, MoveNet phase={movenet_phase}"
            )
            return False

        render_dashboard(yolo, movenet)

        key = read_key(1)
        if key == ord("q"):
            return False

        time.sleep(0.05)


def wait_idle(thread, name, yolo, movenet, timeout_sec=10.0):
    start = time.monotonic()

    while True:
        phase = get_phase(thread)

        if phase in {"idle", "stopped", "error"}:
            return True

        if time.monotonic() - start >= timeout_sec:
            dlog(f"[TEST] Timeout waiting for {name} idle. phase={phase}")
            return False

        render_dashboard(yolo, movenet)

        key = read_key(1)
        if key == ord("q"):
            return False

        time.sleep(0.05)


def stop_thread_processing(thread, name, yolo, movenet):
    if thread.is_active():
        thread.deactivate()
        return wait_idle(thread, name, yolo, movenet)

    return True


def run_yolo_person_gate(yolo, movenet, timeout_sec=30.0):
    dlog("[TEST] Starting YOLO person gate")

    if movenet.is_active():
        movenet.deactivate()
        if not wait_idle(movenet, "MoveNet", yolo, movenet):
            return None

    yolo.activate()

    start = time.monotonic()

    while True:
        render_dashboard(yolo, movenet)

        key = read_key(1)

        if key == ord("q"):
            return None

        if key == ord("0"):
            dlog("[TEST] Simulated tag change during YOLO gate -> stopping YOLO")
            yolo.deactivate()
            wait_idle(yolo, "YOLO", yolo, movenet)
            return False

        phase = get_phase(yolo)

        if phase == "error":
            dlog("[TEST] YOLO entered error phase")
            return False

        person_detected, ts = yolo.get_latest_result()

        if person_detected is True:
            dlog("[TEST] YOLO gate PASSED: person detected")
            return True

        if time.monotonic() - start >= timeout_sec:
            dlog("[TEST] YOLO gate FAILED: no person detected")

            yolo.deactivate()
            wait_idle(yolo, "YOLO", yolo, movenet)

            return False

        time.sleep(0.01)


def keep_yolo_until_tag_change(yolo, movenet):
    dlog("[TEST] Keeping YOLO active")
    dlog("[TEST] Press 0 to simulate tag change")

    while True:
        render_dashboard(yolo, movenet)

        key = read_key(1)

        if key == ord("q"):
            return None

        if key == ord("0"):
            dlog("[TEST] Simulated tag change -> stopping YOLO")

            yolo.deactivate()
            wait_idle(yolo, "YOLO", yolo, movenet)

            return True

        phase = get_phase(yolo)

        if phase == "idle" and not yolo.is_active():
            dlog("[TEST] YOLO stopped itself")
            return True

        if phase == "error":
            dlog("[TEST] YOLO entered error phase")
            return False

        time.sleep(0.01)


def run_movenet_until_tag_change(yolo, movenet):
    dlog("[TEST] Starting MoveNet until tag change")

    if yolo.is_active():
        yolo.deactivate()
        if not wait_idle(yolo, "YOLO", yolo, movenet):
            return None

    movenet.activate()

    confirmed = False
    printed_first_keypoints = False
    printed_first_status = False
    last_status = None

    dlog("[TEST] MoveNet active")
    dlog("[TEST] Waiting for wrist-to-face confirmation")
    dlog("[TEST] Press 0 to simulate tag change")

    while True:
        render_dashboard(yolo, movenet)

        key = read_key(1)

        if key == ord("q"):
            return None

        if key == ord("0"):
            dlog("[TEST] Simulated tag change -> stopping MoveNet")

            movenet.deactivate()
            wait_idle(movenet, "MoveNet", yolo, movenet)

            return confirmed

        phase = get_phase(movenet)

        if phase == "error":
            dlog("[TEST] MoveNet entered error phase")
            return False

        if phase == "idle" and not movenet.is_active():
            dlog("[TEST] MoveNet stopped itself")
            return confirmed

        keypoints, keypoints_ts = movenet.get_latest_result()

        if keypoints is not None and not printed_first_keypoints:
            dlog(f"[TEST] MoveNet produced {len(keypoints)} keypoints")
            printed_first_keypoints = True

        status, distances, ratios, status_ts = movenet.get_latest_status()

        if not printed_first_status and status_ts is not None:
            dlog(
                "[TEST] MoveNet status stream active. "
                f"status={status}, distances={distances}, ratios={ratios}"
            )
            printed_first_status = True

        if status != last_status and status_ts is not None:
            dlog(
                "[TEST] MoveNet proximity status changed: "
                f"{status}, ratios={ratios}"
            )
            last_status = status

        if status is True:
            confirmed = True

        time.sleep(0.01)


def simulate_event(tag, yolo, movenet):
    """
    Simulate dispatcher behavior.

    tag=1 -> NON_DANGEROUS:
        YOLO person gate.
        If person detected, actuation would happen.
        YOLO stays active until simulated tag change.

    tag=2 -> DANGEROUS:
        YOLO person gate.
        If person detected, switch to MoveNet.
        MoveNet stays active until simulated tag change.

    Press 0 to simulate a tag change.
    Press q to quit.
    """
    if tag == 1:
        dlog("[TEST] Simulated NON_DANGEROUS event")

        person_ok = run_yolo_person_gate(
            yolo,
            movenet,
            timeout_sec=30.0
        )

        if person_ok is None:
            return False

        if person_ok:
            dlog("[TEST] RESULT: NON_DANGEROUS actuation would be TRIGGERED")

            keep_running = keep_yolo_until_tag_change(yolo, movenet)

            if keep_running is None:
                return False

        else:
            dlog("[TEST] RESULT: NON_DANGEROUS actuation GATED")

        return True

    if tag == 2:
        dlog("[TEST] Simulated DANGEROUS event")

        person_ok = run_yolo_person_gate(
            yolo,
            movenet,
            timeout_sec=30.0
        )

        if person_ok is None:
            return False

        if not person_ok:
            dlog("[TEST] RESULT: DANGEROUS actuation GATED by YOLO")
            return True

        movenet_ok = run_movenet_until_tag_change(yolo, movenet)

        if movenet_ok is None:
            return False

        if movenet_ok:
            dlog("[TEST] RESULT: DANGEROUS actuation would be TRIGGERED")
        else:
            dlog("[TEST] RESULT: DANGEROUS actuation GATED by MoveNet")

        return True

    dlog(f"[TEST] Simulated tag={tag}: no video pipeline needed")

    stop_thread_processing(yolo, "YOLO", yolo, movenet)
    stop_thread_processing(movenet, "MoveNet", yolo, movenet)

    return True


def shutdown_threads(yolo, movenet):
    yolo.deactivate()
    movenet.deactivate()

    wait_idle(yolo, "YOLO", yolo, movenet, timeout_sec=3.0)
    wait_idle(movenet, "MoveNet", yolo, movenet, timeout_sec=3.0)

    yolo.stop()
    movenet.stop()


def main():
    global dashboard

    yolo = None
    movenet = None

    try:
        yolo = YoloDpuThread(
            camera_index=0,
            debug_window=False
        )

        movenet = MoveNetDpuThread(
            camera_index=0,
            debug_window=False
        )

        dashboard = VideoDashboard(
            window_name="CPSA Dashboard",
            fullscreen=False
        )

        dlog("[TEST] Starting YOLO and MoveNet threads")

        yolo.start()
        movenet.start()

        dlog("[TEST] Waiting for model threads to become ready")

        if not wait_phase_ready(yolo, movenet, timeout_sec=20.0):
            return

        dlog("[TEST] Ready")
        dlog("[TEST] Press 1 for NON_DANGEROUS")
        dlog("[TEST] Press 2 for DANGEROUS")
        dlog("[TEST] Press 0 to simulate tag change while a model is active")
        dlog("[TEST] Press q to quit")

        while True:
            render_dashboard(yolo, movenet)

            key = read_key(1)

            if key == ord("q"):
                break

            if key == ord("1"):
                keep_running = simulate_event(
                    1,
                    yolo,
                    movenet
                )

                if not keep_running:
                    break

                dlog("[TEST] Waiting for next trigger")

            elif key == ord("2"):
                keep_running = simulate_event(
                    2,
                    yolo,
                    movenet
                )

                if not keep_running:
                    break

                dlog("[TEST] Waiting for next trigger")

            time.sleep(0.01)

    except KeyboardInterrupt:
        dlog("[TEST] Stopping")

    finally:
        if yolo is not None and movenet is not None:
            shutdown_threads(yolo, movenet)

        if dashboard is not None:
            dashboard.close()

        print("[TEST] Done")


if __name__ == "__main__":
    main()