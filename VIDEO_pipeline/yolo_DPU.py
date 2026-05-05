import cv2
import numpy as np
import vart
import xir
import threading
import time

from utils.config import get_dpu_path


# ---------------------- CLASS NAMES ---------------------- #
# YOLOv3 trained on VOC dataset can detect these 20 classes.
CLASS_NAMES = [
    "aeroplane", "bicycle", "bird", "boat", "bottle",
    "bus", "car", "cat", "chair", "cow", "diningtable",
    "dog", "horse", "motorbike", "person", "pottedplant",
    "sheep", "sofa", "train", "tvmonitor"
]


# ---------------------- PREPROCESS FUNCTION ---------------------- #
def preprocess(frame, input_shape):
    """
    Resize and normalize a webcam frame for the DPU model.

    Args:
        frame (np.ndarray): Original frame from webcam.
        input_shape (tuple): Shape expected by the DPU model.

    Returns:
        np.ndarray: Preprocessed image ready for inference.

    Why necessary:
        - YOLOv3 expects input images of fixed size, e.g. 416x416.
        - Pixel values are normalized between 0 and 1.
        - The array is made contiguous for DPU/VART access.
    """
    height, width = input_shape[1], input_shape[2]
    image = cv2.resize(frame, (width, height))
    image = image.astype(np.float32) / 255.0
    image = np.ascontiguousarray(image)
    return image


# ---------------------- SIGMOID FUNCTION ---------------------- #
def sigmoid(x):
    """
    Apply sigmoid activation function.

    Args:
        x (float or np.ndarray): Input value(s).

    Returns:
        Same shape as x with sigmoid applied.

    Why necessary:
        - YOLOv3 outputs raw logits for coordinates, objectness, and classes.
        - Sigmoid maps them to [0, 1], representing probabilities.
    """
    return 1 / (1 + np.exp(-x))


# ---------------------- POSTPROCESS FUNCTION ---------------------- #
def postprocess(output, frame, conf_threshold=0.6, nms_threshold=0.4):
    """
    Convert YOLOv3 DPU output into bounding boxes on the original frame.

    Args:
        output (np.ndarray): Raw output from DPU, expected shape [1, 13, 13, 75].
        frame (np.ndarray): Original frame to draw boxes on.
        conf_threshold (float): Minimum confidence to display detection.
        nms_threshold (float): Threshold for Non-Maximum Suppression.

    Returns:
        tuple:
            frame (np.ndarray): Frame with bounding boxes drawn.
            person_detected (bool): True if at least one detected class is "person".

    Steps:
        1. Reshape output to (grid_h, grid_w, anchors, attributes).
        2. Convert model outputs to absolute bounding boxes.
        3. Apply confidence thresholding.
        4. Apply Non-Maximum Suppression to remove duplicates.
        5. Draw bounding boxes and labels.
        6. Return whether a person was detected.
    """
    H, W = frame.shape[:2]

    # YOLOv3 VOC predefined anchors for the 13x13 scale.
    anchors = [(116, 90), (156, 198), (373, 326)]
    grid_size = 13
    num_anchors = 3
    num_classes = 20

    # Reshape output to [grid_h, grid_w, anchors, 5 + num_classes].
    output = output.reshape(grid_size, grid_size, num_anchors, 5 + num_classes)

    boxes = []
    confidences = []
    class_ids = []

    # Iterate through all grid cells and anchors.
    for row in range(grid_size):
        for col in range(grid_size):
            for a in range(num_anchors):
                tx, ty, tw, th, obj_score = output[row, col, a, :5]
                obj_score = sigmoid(obj_score)

                if obj_score < conf_threshold:
                    continue

                # Compute normalized bounding box center.
                bx = (sigmoid(tx) + col) / grid_size
                by = (sigmoid(ty) + row) / grid_size

                # Compute normalized width and height using anchor priors.
                bw = np.exp(tw) * anchors[a][0] / 416
                bh = np.exp(th) * anchors[a][1] / 416

                # Convert normalized coordinates to pixel coordinates.
                x = int((bx - bw / 2) * W)
                y = int((by - bh / 2) * H)
                w = int(bw * W)
                h = int(bh * H)

                # Determine predicted class and final confidence.
                class_probs = sigmoid(output[row, col, a, 5:])
                class_id = np.argmax(class_probs)
                confidence = obj_score * class_probs[class_id]

                if confidence > conf_threshold:
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

    # Remove overlapping detections.
    indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

    # Draw bounding boxes and labels.
    if len(indices) > 0:
        for i in indices.flatten():
            x, y, w, h = boxes[i]
            label = CLASS_NAMES[class_ids[i]]
            conf = confidences[i]

            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"{label} {conf:.2f}",
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )

    # For the current CPSA logic, the DPU acts as a person-presence gate.
    person_detected = (
        any(CLASS_NAMES[class_ids[i]] == "person" for i in indices.flatten())
        if len(indices) > 0
        else False
    )

    return frame, person_detected


# ------------------- YOLO DPU THREAD ------------------- #
class YoloDpuThread(threading.Thread):
    """
    Thread that controls the USB camera and runs YOLOv3 inference on the DPU.

    This thread:
        - Initializes the DPU runner once.
        - Waits idle until activated by the IMU/event dispatcher.
        - Opens the camera only while active.
        - Runs YOLO inference on camera frames.
        - Stores the latest person-detection result.
        - Deactivates itself if no person is detected for a timeout window.
    """

    def __init__(self, device_id: str = "camera0", camera_index: int = 0):
        """
        Initialize the YOLO DPU camera thread.

        Args:
            device_id (str): Logical identifier for the camera sensor.
            camera_index (int): OpenCV camera index, usually 0 for the default USB camera.
        """
        super().__init__(daemon=True)
        self.device_id = device_id
        self.camera_index = camera_index

        # Thread lifecycle events.
        self.stop_event = threading.Event()
        self.active_event = threading.Event()

        # Camera and DPU runner handles.
        self.cap = None
        self.runner = None

        # Shared latest result.
        self.result_lock = threading.Lock()
        self.latest_result = None
        self.latest_result_ts = None

        # Auto-deactivation when no person is visible.
        self.no_person_timeout_sec = 5.0
        self._last_person_seen_ts = None

    def activate(self):
        """Activate YOLO processing. The camera is opened by run() when this flag is set."""
        self.active_event.set()

    def deactivate(self):
        """
        Deactivate YOLO processing and clear the latest DPU result.

        This does not terminate the thread; it only returns the camera/DPU loop to idle.
        """
        self.active_event.clear()
        self._last_person_seen_ts = None

        with self.result_lock:
            self.latest_result = None
            self.latest_result_ts = None

    def get_latest_result(self):
        """
        Return the latest person-detection result.

        Returns:
            tuple:
                latest_result:
                    True  -> person detected.
                    False -> no person detected.
                    None  -> no current DPU result.
                latest_result_ts:
                    time.monotonic() timestamp of the latest result, or None.
        """
        with self.result_lock:
            return self.latest_result, self.latest_result_ts

    def is_active(self):
        """Return True if the YOLO camera loop is currently active."""
        return self.active_event.is_set()

    def run(self):
        """
        Main thread loop.

        The DPU model is loaded once. The thread then waits for activation.
        When active, it opens the camera, processes frames, updates person detection,
        and closes the camera when deactivated or when no person is detected for the timeout.
        """
        model_path = get_dpu_path()

        # Load the compiled xmodel graph.
        graph = xir.Graph.deserialize(model_path)

        # Find the DPU subgraph.
        dpu_subgraph = [
            sg for sg in graph.get_root_subgraph().toposort_child_subgraph()
            if sg.has_attr("device") and sg.get_attr("device").upper() == "DPU"
        ][0]

        # Create the VART runner.
        self.runner = vart.Runner.create_runner(dpu_subgraph, "run")

        # Read tensor information from the runner.
        input_tensors = self.runner.get_input_tensors()
        output_tensors = self.runner.get_output_tensors()
        input_shape = tuple(input_tensors[0].dims)

        # Wait for activation requests until shutdown.
        while not self.stop_event.is_set():
            if not self.active_event.wait(timeout=0.5):
                continue

            # Open camera only while active.
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                from utils.logger import log_system
                log_system("[YoloDpuThread] Webcam not found", level="ERROR")
                self.active_event.clear()
                continue

            # Set camera resolution.
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Allocate output buffers for the DPU.
            output_data = [
                np.empty(tuple(ot.dims), dtype=np.float32)
                for ot in output_tensors
            ]

            # Start no-person timeout once the camera is actually active.
            self._last_person_seen_ts = time.monotonic()

            while self.active_event.is_set() and not self.stop_event.is_set():
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Preprocess current frame.
                img_input = preprocess(frame, input_shape)

                # Run inference on DPU.
                job_id = self.runner.execute_async([img_input], output_data)
                self.runner.wait(job_id)

                # Convert raw model output into visual detections and person flag.
                frame, person_detected = postprocess(output_data[0], frame)

                now = time.monotonic()

                # Refresh timeout while a person is visible.
                if person_detected:
                    self._last_person_seen_ts = now
                else:
                    if self._last_person_seen_ts is not None and (
                        now - self._last_person_seen_ts
                    ) >= self.no_person_timeout_sec:
                        self.deactivate()
                        break

                # Publish latest result for EventDispatcher gating logic.
                with self.result_lock:
                    self.latest_result = person_detected
                    self.latest_result_ts = time.monotonic()

                # Display debug window.
                cv2.imshow("YOLOv3 DPU", frame)
                cv2.waitKey(1)

            # Release camera whenever the active phase ends.
            if self.cap:
                self.cap.release()
                self.cap = None

            cv2.destroyAllWindows()

        # Release runner reference on shutdown.
        self.runner = None

    def stop(self):
        """
        Stop the thread and wake it if it is currently waiting for activation.
        """
        self.stop_event.set()
        self.active_event.set()

        if self.is_alive():
            self.join()