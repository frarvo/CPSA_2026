# test_yolo_dpu_thread.py

import time
from VIDEO_pipeline.YOLO.yolo_thread import YoloDpuThread
# Adjust import if your file name/path is different.


def main():
    yolo = YoloDpuThread(camera_index=0)

    print("[TEST] Starting YOLO thread")
    yolo.start()

    print("[TEST] Waiting 10s while YOLO thread is idle")
    time.sleep(10)

    print("[TEST] Activating YOLO")
    yolo.activate()

    try:
        while True:
            if not yolo.is_alive():
                print("[TEST] YOLO thread died.")
                break

            result, ts = yolo.get_latest_result()

            print(
                f"[TEST] active={yolo.is_active()} | "
                f"person_detected={result} | ts={ts}"
            )

            if not yolo.is_active():
                print("[TEST] YOLO inactive. Reactivating in 20s.")
                time.sleep(20)
                yolo.activate()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[TEST] Stopping YOLO")
        yolo.stop()
        print("[TEST] Done")


if __name__ == "__main__":
    main()