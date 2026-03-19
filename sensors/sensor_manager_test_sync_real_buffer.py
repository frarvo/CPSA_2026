import time
from sensor_manager import SensorManager

def Rgyr_str(g):
    # optional tiny helper for formatting
    return f"({g[0]:.3f}, {g[1]:.3f}, {g[2]:.3f})"

def main():
    sm = SensorManager()

    # Normal startup
    sm.scan_sensors()
    sm.initialize_sensors()

    print("Running. 'Synchronized Buffer Row' Should appear as data arrives.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        sm.stop_all()

if __name__ == "__main__":
    main()