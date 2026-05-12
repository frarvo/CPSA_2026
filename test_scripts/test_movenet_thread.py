# test_movenet_thread.py

import time

from VIDEO_pipeline.MOVENET.movenet_thread import MoveNetDpuThread
# Adjust import if your file name/path is different.


def main():
    movenet = MoveNetDpuThread(camera_index=0)

    print("[TEST] Starting MoveNet thread")
    movenet.start()

    print("[TEST] Waiting 10s while MoveNet thread is idle")
    time.sleep(10)

    print("[TEST] Activating MoveNet")
    movenet.activate()

    try:
        while True:
            if not movenet.is_alive():
                print("[TEST] MoveNet thread died.")
                break

            result, ts = movenet.get_latest_result()

            num_keypoints = len(result) if result is not None else None

            print(
                f"[TEST] active={movenet.is_active()} | "
                f"keypoints={num_keypoints} | ts={ts}"
            )

            if not movenet.is_active():
                print("[TEST] MoveNet inactive. Reactivating in 20s.")
                time.sleep(20)
                movenet.activate()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[TEST] Stopping MoveNet")
        movenet.stop()
        print("[TEST] Done")


if __name__ == "__main__":
    main()