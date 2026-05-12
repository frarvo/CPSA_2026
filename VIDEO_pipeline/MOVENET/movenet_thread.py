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
    0,       # nose

    5, 6,    # shoulders
    7, 8,    # elbows
    9, 10    # wrists
}

SKELETON = [
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
]

ROI_MAX_AGE_SEC = 1.0

# When using a YOLO bbox, expand it before cropping.
# The bbox can be slightly stale because YOLO and MoveNet do not run on the same frame.
YOLO_ROI_MARGIN_X = 0.25
YOLO_ROI_MARGIN_Y = 0.35

# minimum keypoint score used to build a new ROI
MOVENET_ROI_MIN_SCORE = 0.25
# minimum number of visible upper-body keypoints needed
MOVENET_ROI_MIN_KEYPOINTS = 3

# expansion applied to the bbox generated from keypoints
MOVENET_ROI_MARGIN_X = 0.60
MOVENET_ROI_MARGIN_Y = 0.80

# below this average score, consider MoveNet tracking unreliable
MOVENET_REACQUIRE_SCORE = 0.20
# number of consecutive weak frames before asking YOLO to reacquire
MOVENET_REACQUIRE_BAD_FRAMES = 3


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


# ---------------------------------------------------------
# IMAGE PROCESSING
# ---------------------------------------------------------

def clamp_bbox_xyxy(x1, y1, x2, y2, img_w, img_h):
    x1 = max(0, min(img_w - 1, int(x1)))
    y1 = max(0, min(img_h - 1, int(y1)))
    x2 = max(0, min(img_w, int(x2)))
    y2 = max(0, min(img_h, int(y2)))

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


def expand_bbox_xyxy(
    bbox_xyxy,
    img_w,
    img_h,
    margin_x=0.25,
    margin_y=0.35
):
    if bbox_xyxy is None:
        return None

    x1, y1, x2, y2 = bbox_xyxy

    w = x2 - x1
    h = y2 - y1

    if w <= 0 or h <= 0:
        return None

    dx = int(w * margin_x)
    dy = int(h * margin_y)

    return clamp_bbox_xyxy(
        x1 - dx,
        y1 - dy,
        x2 + dx,
        y2 + dy,
        img_w,
        img_h
    )


def letterbox_image(image, target_w, target_h, color=(0, 0, 0)):
    """
    Resize image with unchanged aspect ratio using padding.

    Returns:
        out:
            Letterboxed image of shape target_h x target_w x C.

        scale:
            Resize scale from original crop to resized crop.

        pad_left:
            Horizontal padding on the left.

        pad_top:
            Vertical padding on the top.
    """
    h, w = image.shape[:2]

    scale = min(target_w / float(w), target_h / float(h))

    new_w = int(round(w * scale))
    new_h = int(round(h * scale))

    resized = cv2.resize(
        image,
        (new_w, new_h),
        interpolation=cv2.INTER_LINEAR
    )

    pad_w = target_w - new_w
    pad_h = target_h - new_h

    pad_left = pad_w // 2
    pad_right = pad_w - pad_left
    pad_top = pad_h // 2
    pad_bottom = pad_h - pad_top

    out = cv2.copyMakeBorder(
        resized,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_CONSTANT,
        value=color
    )

    return out, scale, pad_left, pad_top


def preprocess(frame, input_shape, input_tensor, roi_bbox=None):
    """
    MoveNet input:
        192x192 RGB int8 or float, depending on xmodel input tensor.

    New behavior:
        - if roi_bbox is available, crop the frame around the ROI
        - otherwise, use the full frame
        - letterbox the crop/full frame to the model input size
        - return transform metadata for decoding keypoints back to full-frame coordinates
    """
    target_h, target_w = input_shape[1], input_shape[2]
    img_h, img_w = frame.shape[:2]

    if roi_bbox is not None:
        expanded = expand_bbox_xyxy(
            roi_bbox,
            img_w,
            img_h,
            margin_x=YOLO_ROI_MARGIN_X,
            margin_y=YOLO_ROI_MARGIN_Y
        )
    else:
        expanded = None

    if expanded is None:
        # Fallback: use the full frame, but still letterbox.
        crop_x1, crop_y1, crop_x2, crop_y2 = 0, 0, img_w, img_h
        crop_source = "full_frame"
    else:
        crop_x1, crop_y1, crop_x2, crop_y2 = expanded
        crop_source = "roi"

    crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

    letterboxed, scale, pad_left, pad_top = letterbox_image(
        crop,
        target_w,
        target_h
    )

    image = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)

    fix_point = get_fix_point(input_tensor)

    if fix_point is not None:
        quant_scale = 2 ** fix_point

        image = image.astype(np.float32) / 255.0
        image = image * quant_scale
        image = np.clip(image, -128, 127).astype(np.int8)

    else:
        image = image.astype(np.float32) / 255.0

    transform = {
        "crop_source": crop_source,
        "crop_x1": crop_x1,
        "crop_y1": crop_y1,
        "crop_x2": crop_x2,
        "crop_y2": crop_y2,
        "crop_w": crop_x2 - crop_x1,
        "crop_h": crop_y2 - crop_y1,
        "scale": scale,
        "pad_left": pad_left,
        "pad_top": pad_top,
        "target_w": target_w,
        "target_h": target_h,
    }

    return np.ascontiguousarray(image.reshape(input_shape)), crop.copy(), transform

# ---------------------------------------------------------
# KEYPOINT DECODING
# ---------------------------------------------------------

def decode_keypoints(
    heatmaps,
    offsets,
    transform,
    frame_shape,
    score_threshold=0.10
):
    """
    Decode MoveNet heatmaps + offsets.

    Expected outputs:
        heatmaps : (1, 48, 48, 17)
        offsets  : (1, 48, 48, 34)

    Coordinates are returned in full-frame coordinates.
    """
    frame_h, frame_w = frame_shape[:2]

    heatmaps = heatmaps[0]
    offsets = offsets[0]

    crop_x1 = transform["crop_x1"]
    crop_y1 = transform["crop_y1"]
    scale = transform["scale"]
    pad_left = transform["pad_left"]
    pad_top = transform["pad_top"]

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

        # Undo letterbox:
        # model coordinates -> crop coordinates
        x_crop = (x_192 - pad_left) / scale
        y_crop = (y_192 - pad_top) / scale

        # Crop coordinates -> full-frame coordinates
        x_full = x_crop + crop_x1
        y_full = y_crop + crop_y1

        x = int(round(x_full))
        y = int(round(y_full))

        x = max(0, min(frame_w - 1, x))
        y = max(0, min(frame_h - 1, y))

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
# DISTANCE / NORMALIZED FACE PROXIMITY CHECK
# ---------------------------------------------------------

NOSE_ID = 0
LEFT_SHOULDER_ID = 5
RIGHT_SHOULDER_ID = 6
LEFT_WRIST_ID = 9
RIGHT_WRIST_ID = 10


def distance_between(a, b):
    dx = float(a["x"] - b["x"])
    dy = float(a["y"] - b["y"])
    return float(np.sqrt(dx * dx + dy * dy))

def upper_body_score(keypoints):
    """
    Average score over visible upper-body keypoints.

    Uses the same upper-body IDs already relevant for the wrist-to-face task.
    """
    if not keypoints:
        return 0.0

    valid_scores = [
        float(kp["score"])
        for kp in keypoints
        if kp["id"] in VALID_KEYPOINT_IDS and kp["visible"]
    ]

    if not valid_scores:
        return 0.0

    return float(np.mean(valid_scores))


def bbox_from_keypoints(
    keypoints,
    frame_shape,
    min_score=MOVENET_ROI_MIN_SCORE,
    min_keypoints=MOVENET_ROI_MIN_KEYPOINTS
):
    """
    Build a full-frame xyxy ROI from confident MoveNet upper-body keypoints.

    Returns:
        bbox_xyxy, confidence

        bbox_xyxy:
            (x1, y1, x2, y2) in full-frame coordinates,
            or None if not enough reliable keypoints exist.

        confidence:
            average score of the keypoints used to build the bbox.
    """
    frame_h, frame_w = frame_shape[:2]

    valid = [
        kp for kp in keypoints
        if (
            kp["id"] in VALID_KEYPOINT_IDS
            and kp["visible"]
            and float(kp["score"]) >= min_score
        )
    ]

    if len(valid) < min_keypoints:
        return None, 0.0

    xs = np.array([kp["x"] for kp in valid], dtype=np.float32)
    ys = np.array([kp["y"] for kp in valid], dtype=np.float32)
    scores = np.array([kp["score"] for kp in valid], dtype=np.float32)

    x1 = float(xs.min())
    y1 = float(ys.min())
    x2 = float(xs.max())
    y2 = float(ys.max())

    if x2 <= x1 or y2 <= y1:
        return None, 0.0

    bbox = expand_bbox_xyxy(
        (x1, y1, x2, y2),
        frame_w,
        frame_h,
        margin_x=MOVENET_ROI_MARGIN_X,
        margin_y=MOVENET_ROI_MARGIN_Y
    )

    if bbox is None:
        return None, 0.0

    confidence = float(scores.mean())

    return bbox, confidence

def normalized_wrist_to_face_status(
    keypoints,
    threshold_ratio=0.45,
    require_both_wrists=False
):
    """
    Face proximity check using only the nose as face reference.

    Normalization:
        wrist_to_nose_distance / shoulder_width

    This makes the threshold less dependent on camera distance.

    Returns:
        status: True or False
        distances: raw wrist-to-nose distances in crop pixels
        ratios: normalized distances
    """
    if not keypoints:
        return False, {}, {}

    points = {kp["id"]: kp for kp in keypoints}

    nose = points.get(NOSE_ID)
    left_shoulder = points.get(LEFT_SHOULDER_ID)
    right_shoulder = points.get(RIGHT_SHOULDER_ID)
    left_wrist = points.get(LEFT_WRIST_ID)
    right_wrist = points.get(RIGHT_WRIST_ID)

    if nose is None or not nose["visible"]:
        return False, {}, {}

    if (
        left_shoulder is None
        or right_shoulder is None
        or not left_shoulder["visible"]
        or not right_shoulder["visible"]
    ):
        return False, {}, {}

    shoulder_width = distance_between(left_shoulder, right_shoulder)

    if shoulder_width <= 1.0:
        return False, {}, {}

    distances = {}
    ratios = {}

    if left_wrist is not None and left_wrist["visible"]:
        d = distance_between(left_wrist, nose)
        distances["left_wrist_to_face"] = d
        ratios["left_wrist_to_face"] = d / shoulder_width

    if right_wrist is not None and right_wrist["visible"]:
        d = distance_between(right_wrist, nose)
        distances["right_wrist_to_face"] = d
        ratios["right_wrist_to_face"] = d / shoulder_width

    if require_both_wrists:
        status = (
            "left_wrist_to_face" in ratios
            and "right_wrist_to_face" in ratios
            and ratios["left_wrist_to_face"] <= threshold_ratio
            and ratios["right_wrist_to_face"] <= threshold_ratio
        )
    else:
        status = any(r <= threshold_ratio for r in ratios.values())

    return status, distances, ratios


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
        - wrist-to-face proximity status

    GUI rule:
        By default, this thread does not create its own OpenCV window.
        The dashboard should own cv2.imshow() and cv2.waitKey().
    """

    def __init__(
        self,
        device_id: str = "camera0",
        camera_index: int = 0,
        debug_window: bool = False,
        roi_state=None
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

        self.latest_status = False
        self.latest_distances = {}
        self.latest_ratios = {}

        self.movenet_bad_roi_frames = 0

        self.roi_state = roi_state

        # Used by wait_idle() in your dashboard test.
        self.phase = "idle"

    # -----------------------------------------------------

    def activate(self):
        self.active_event.set()

    def deactivate(self):
        self.active_event.clear()
        self.movenet_bad_roi_frames = 0

        with self.result_lock:
            self.latest_keypoints = None
            self.latest_result_ts = None
            self.latest_frame = None
            self.latest_status = False
            self.latest_distances = {}
            self.latest_ratios = {}

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

    def get_latest_status(self):
        with self.result_lock:
            return (
                self.latest_status,
                self.latest_distances,
                self.latest_ratios,
                self.latest_result_ts
            )

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

                    # Keep MoveNet and YOLO in the same mirrored camera coordinate system.
                    frame = cv2.flip(frame, 1)

                    roi_bbox = None

                    if self.roi_state is not None:
                        roi_bbox = self.roi_state.get_valid_roi(
                            max_age_sec=ROI_MAX_AGE_SEC
                        )

                    img_input, crop_view, transform = preprocess(
                        frame,
                        input_shape,
                        input_tensor,
                        roi_bbox=roi_bbox
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


                    keypoints = decode_keypoints(
                        heatmaps=heatmaps,
                        offsets=offsets,
                        transform=transform,
                        frame_shape=frame.shape,
                        score_threshold=0.10
                    )

                    status, distances, ratios = normalized_wrist_to_face_status(
                        keypoints,
                        threshold_ratio=0.45,
                        require_both_wrists=False
                    )

                    pose_score = upper_body_score(keypoints)

                    if self.roi_state is not None:
                        if pose_score < MOVENET_REACQUIRE_SCORE:
                            self.movenet_bad_roi_frames += 1

                            if self.movenet_bad_roi_frames >= MOVENET_REACQUIRE_BAD_FRAMES:
                                self.roi_state.mark_reacquire()
                        else:
                            self.movenet_bad_roi_frames = 0

                            if not self.roi_state.needs_reacquire():
                                updated_bbox, updated_conf = bbox_from_keypoints(
                                    keypoints,
                                    frame.shape
                                )

                                if updated_bbox is not None:
                                    self.roi_state.update_from_movenet(
                                        bbox_xyxy=updated_bbox,
                                        confidence=updated_conf
                                    )

                    debug_view = frame.copy()

                    # Draw the active MoveNet crop region.
                    cv2.rectangle(
                        debug_view,
                        (transform["crop_x1"], transform["crop_y1"]),
                        (transform["crop_x2"], transform["crop_y2"]),
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        debug_view,
                        transform["crop_source"],
                        (transform["crop_x1"], max(0, transform["crop_y1"] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1
                    )
                    cv2.putText(
                        debug_view,
                        f"pose_score={pose_score:.2f}",
                        (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 255),
                        2
                    )

                    debug_view = draw_keypoints(
                        debug_view,
                        keypoints
                    )

                    model_view = cv2.resize(
                        debug_view,
                        (display_w, display_h),
                        interpolation=cv2.INTER_NEAREST
                    )

                    now = time.monotonic()

                    with self.result_lock:
                        self.latest_keypoints = keypoints
                        self.latest_result_ts = now
                        self.latest_frame = model_view.copy()
                        self.latest_status = status
                        self.latest_distances = distances
                        self.latest_ratios = ratios

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
                    self.latest_status = False
                    self.latest_distances = {}
                    self.latest_ratios = {}

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