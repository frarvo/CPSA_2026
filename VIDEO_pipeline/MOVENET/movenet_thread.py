# movenet_thread.py

import cv2
import numpy as np
import vart
import xir
import threading
import time

from utils.config import get_movenet_path


# ---------------------------------------------------------
# KEYPOINTS
# ---------------------------------------------------------

KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

VALID_KEYPOINT_IDS = {
    0, 1, 2, 3, 4,
    5, 6,
    7, 8,
    9, 10
}

SKELETON = [
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
]


# ---------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def get_dpu_subgraph(graph):
    subgraphs = [
        sg for sg in graph.get_root_subgraph().toposort_child_subgraph()
        if sg.has_attr("device") and sg.get_attr("device").upper() == "DPU"
    ]

    if len(subgraphs) != 1:
        raise RuntimeError(f"Expected 1 DPU subgraph, found {len(subgraphs)}")

    return subgraphs[0]


def get_fix_point(tensor):
    return tensor.get_attr("fix_point") if tensor.has_attr("fix_point") else None


def dequantize(output, tensor):
    fix_point = get_fix_point(tensor)

    if fix_point is None:
        return output.astype(np.float32)

    return output.astype(np.float32) / float(2 ** fix_point)


# ---------------------------------------------------------
# IMAGE PROCESSING
# ---------------------------------------------------------

def center_crop_square(frame):
    """
    Convert:
        640x480 -> 480x480 center crop
    """
    H, W = frame.shape[:2]

    crop_size = min(H, W)

    start_x = (W - crop_size) // 2
    start_y = (H - crop_size) // 2

    cropped = frame[
        start_y:start_y + crop_size,
        start_x:start_x + crop_size
    ]

    return cropped


def preprocess(frame, input_shape, input_tensor):
    """
    MoveNet input:
        192x192 RGB int8
    """
    target_h, target_w = input_shape[1], input_shape[2]

    cropped = center_crop_square(frame)

    image = cv2.resize(cropped, (target_w, target_h))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    fix_point = get_fix_point(input_tensor)

    if fix_point is not None:
        scale = 2 ** fix_point

        image = image.astype(np.float32) / 255.0
        image = image * scale
        image = np.clip(image, -128, 127).astype(np.int8)

    else:
        image = image.astype(np.float32) / 255.0

    return np.ascontiguousarray(image.reshape(input_shape))


# ---------------------------------------------------------
# KEYPOINT DECODING
# ---------------------------------------------------------

def decode_keypoints(
    heatmaps,
    offsets,
    display_shape,
    score_threshold=0.10
):
    """
    Decode MoveNet heatmaps + offsets.

    Expected outputs:
        heatmaps : (1, 48, 48, 17)
        offsets  : (1, 48, 48, 34)
    """
    H, W = display_shape[:2]

    heatmaps = heatmaps[0]
    offsets = offsets[0]

    keypoints = []

    for keypoint_id in sorted(VALID_KEYPOINT_IDS):
        heatmap = heatmaps[:, :, keypoint_id]

        y_cell, x_cell = np.unravel_index(
            np.argmax(heatmap),
            heatmap.shape
        )

        raw_score = float(heatmap[y_cell, x_cell])
        score = float(sigmoid(raw_score))

        y_offset = float(offsets[y_cell, x_cell, keypoint_id])
        x_offset = float(offsets[y_cell, x_cell, keypoint_id + 17])

        y_192 = y_cell * 4.0 + y_offset
        x_192 = x_cell * 4.0 + x_offset

        x = int((x_192 / 192.0) * W)
        y = int((y_192 / 192.0) * H)

        x = max(0, min(W - 1, x))
        y = max(0, min(H - 1, y))

        keypoints.append({
            "id": keypoint_id,
            "name": KEYPOINT_NAMES[keypoint_id],
            "x": x,
            "y": y,
            "score": score,
            "visible": score >= score_threshold,
        })

    return keypoints


# ---------------------------------------------------------
# VISUALIZATION
# ---------------------------------------------------------

def draw_keypoints(frame, keypoints):
    points = {}

    for kp in keypoints:
        x = kp["x"]
        y = kp["y"]
        visible = kp["visible"]
        score = kp["score"]
        kid = kp["id"]

        points[kid] = (x, y, visible, score)

        if visible:
            cv2.circle(frame, (x, y), 4, (0, 255, 255), -1)

            cv2.putText(
                frame,
                f'{kp["name"]} {score:.2f}',
                (x + 4, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 255, 255),
                1
            )

    for a, b in SKELETON:
        if a not in points or b not in points:
            continue

        xa, ya, va, _ = points[a]
        xb, yb, vb, _ = points[b]

        if va and vb:
            cv2.line(
                frame,
                (xa, ya),
                (xb, yb),
                (255, 0, 0),
                2
            )

    return frame


# ---------------------------------------------------------
# THREAD
# ---------------------------------------------------------

class MoveNetDpuThread(threading.Thread):
    """
    Thread controlling:
        - camera
        - MoveNet DPU inference
        - latest keypoints storage

    GUI rule:
        By default, this thread does not create its own OpenCV window.
        The dashboard should own cv2.imshow() and cv2.waitKey().
    """

    def __init__(
        self,
        device_id: str = "camera0",
        camera_index: int = 0,
        debug_window: bool = False
    ):
        super().__init__(daemon=True)

        self.device_id = device_id
        self.camera_index = camera_index
        self.debug_window = debug_window

        self.stop_event = threading.Event()
        self.active_event = threading.Event()

        self.cap = None
        self.runner = None

        self.result_lock = threading.Lock()

        self.latest_keypoints = None
        self.latest_result_ts = None
        self.latest_frame = None

        # Used by wait_idle() in your dashboard test.
        self.phase = "idle"

    # -----------------------------------------------------

    def activate(self):
        self.active_event.set()

    def deactivate(self):
        self.active_event.clear()

        with self.result_lock:
            self.latest_keypoints = None
            self.latest_result_ts = None
            self.latest_frame = None

    def is_active(self):
        return self.active_event.is_set()

    def get_latest_result(self):
        with self.result_lock:
            return self.latest_keypoints, self.latest_result_ts

    def get_latest_frame(self):
        with self.result_lock:
            if self.latest_frame is None:
                return None

            return self.latest_frame.copy()

    # -----------------------------------------------------

    def run(self):
        try:
            self.phase = "loading"

            model_path = get_movenet_path()

            graph = xir.Graph.deserialize(model_path)

            dpu_subgraph = get_dpu_subgraph(graph)

            self.runner = vart.Runner.create_runner(
                dpu_subgraph,
                "run"
            )

            input_tensors = self.runner.get_input_tensors()
            output_tensors = self.runner.get_output_tensors()

            input_tensor = input_tensors[0]
            input_shape = tuple(input_tensor.dims)

            print("\n[MoveNetDpuThread] Inputs:")
            for t in input_tensors:
                print(
                    t.name,
                    tuple(t.dims),
                    "fix_point=",
                    get_fix_point(t)
                )

            print("\n[MoveNetDpuThread] Outputs:")
            for t in output_tensors:
                print(
                    t.name,
                    tuple(t.dims),
                    "fix_point=",
                    get_fix_point(t)
                )

            display_w = 1080
            display_h = 1080

            self.phase = "idle"

            while not self.stop_event.is_set():

                if not self.active_event.wait(timeout=0.5):
                    self.phase = "idle"
                    continue

                if self.stop_event.is_set():
                    break

                self.phase = "opening_camera"

                self.cap = cv2.VideoCapture(self.camera_index)

                if not self.cap.isOpened():
                    print("[MoveNetDpuThread] Webcam not found")

                    self.active_event.clear()
                    self.phase = "idle"
                    continue

                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

                if self.debug_window:
                    cv2.namedWindow(
                        "MoveNet DPU",
                        cv2.WINDOW_NORMAL
                    )

                    cv2.resizeWindow(
                        "MoveNet DPU",
                        display_w,
                        display_h
                    )

                output_data = [
                    np.empty(
                        tuple(ot.dims),
                        dtype=np.int8
                        if get_fix_point(ot) is not None
                        else np.float32
                    )
                    for ot in output_tensors
                ]

                self.phase = "running"

                while (
                    self.active_event.is_set()
                    and not self.stop_event.is_set()
                ):
                    ret, frame = self.cap.read()

                    if not ret:
                        print("[MoveNetDpuThread] Failed to read frame")
                        break

                    frame = cv2.flip(frame, 1)

                    img_input = preprocess(
                        frame,
                        input_shape,
                        input_tensor
                    )

                    job_id = self.runner.execute_async(
                        [img_input],
                        output_data
                    )

                    self.runner.wait(job_id)

                    heatmaps = dequantize(
                        output_data[1],
                        output_tensors[1]
                    )

                    offsets = dequantize(
                        output_data[2],
                        output_tensors[2]
                    )

                    cropped_view = center_crop_square(frame)

                    keypoints = decode_keypoints(
                        heatmaps=heatmaps,
                        offsets=offsets,
                        display_shape=cropped_view.shape,
                        score_threshold=0.10
                    )

                    cropped_view = draw_keypoints(
                        cropped_view,
                        keypoints
                    )

                    model_view = cv2.resize(
                        cropped_view,
                        (display_w, display_h),
                        interpolation=cv2.INTER_NEAREST
                    )

                    now = time.monotonic()

                    with self.result_lock:
                        self.latest_keypoints = keypoints
                        self.latest_result_ts = now
                        self.latest_frame = model_view.copy()

                    if self.debug_window:
                        cv2.imshow(
                            "MoveNet DPU",
                            model_view
                        )

                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            self.deactivate()
                            break

                self.phase = "closing_camera"

                if self.cap:
                    self.cap.release()
                    self.cap = None

                if self.debug_window:
                    try:
                        cv2.destroyWindow("MoveNet DPU")
                    except cv2.error:
                        pass

                with self.result_lock:
                    self.latest_frame = None

                self.phase = "idle"

        finally:
            if self.cap:
                self.cap.release()
                self.cap = None

            if self.debug_window:
                try:
                    cv2.destroyWindow("MoveNet DPU")
                except cv2.error:
                    pass

            self.runner = None
            self.phase = "stopped"

    # -----------------------------------------------------

    def stop(self):
        self.stop_event.set()

        # Wake thread if blocked in active_event.wait().
        self.active_event.set()

        if self.is_alive():
            self.join(timeout=3.0)