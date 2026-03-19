import time
from sensor_manager import SensorManager

class PrintBuffer:
    def set_features_sink(self, sink):
        # IMUSynchronizer calls this on its buffer in your SensorManager __init__ chain
        # We don't forward features anywhere in this print-only buffer.
        pass

    def add_buffer_row(self, R_acc, R_gyr, R_quat, L_acc, L_gyr, L_quat, ts_emit):
        # Pretty print the synchronized row the moment the sync aligns both wrists
        print("\n=== Synchronized Buffer Row ===")
        print(f"ts_emit: {ts_emit:.6f} (monotonic seconds)")
        print(f"RIGHT  acc:  {R_acc}  gyr: {Rgyr_str(R_gyr)}  quat: {R_quat}")
        print(f"LEFT   acc:  {L_acc}  gyr: {Rgyr_str(L_gyr)}  quat: {L_quat}")

def Rgyr_str(g):
    # optional tiny helper for formatting
    return f"({g[0]:.3f}, {g[1]:.3f}, {g[2]:.3f})"

def main():
    sm = SensorManager()

    # Swap the synchronizer's buffer with our print-only buffer
    sm.synchronizer.buffer = PrintBuffer()

    # Normal startup
    sm.scan_sensors()
    sm.initialize_sensors()

    print("Running. 'Synchronized Buffer Row' Should appear as data arrives.")
    print("   Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        sm.stop_all()

if __name__ == "__main__":
    main()