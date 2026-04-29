import cv2
import numpy as np
import vart
import xir
import threading

import time

from utils.config import get_dpu_path

# ---------------------- CLASS NAMES ---------------------- #
# YOLOv3 trained on VOC dataset can detect these 20 classes
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
        input_shape (tuple): Shape expected by DPU model (N, C, H, W)

    Returns:
        np.ndarray: Preprocessed image ready for inference.

    Why necessary:
        - YOLOv3 expects input images of fixed size (e.g., 416x416)
        - Pixel values need to be normalized between 0 and 1
    """
    height, width = input_shape[1], input_shape[2]
    image = cv2.resize(frame, (width, height))  # Resize image
    image = image.astype(np.float32) / 255.0  # Normalize pixels
    image = np.ascontiguousarray(image)  # Make memory contiguous for efficient DPU access
    return image


# ---------------------- SIGMOID FUNCTION ---------------------- #
def sigmoid(x):
    """
    Apply sigmoid activation function.

    Args:
        x (float or np.ndarray): Input value(s)

    Returns:
        Same shape as x with sigmoid applied

    Why necessary:
        - YOLOv3 outputs bounding box predictions and confidence scores
        - Sigmoid maps them to [0,1], representing probabilities
    """
    return 1 / (1 + np.exp(-x))


# ---------------------- POSTPROCESS FUNCTION ---------------------- #
def postprocess(output, frame, conf_threshold=0.6, nms_threshold=0.4):
    """
    Convert YOLOv3 DPU output into bounding boxes on the original frame.

    Args:
        output (np.ndarray): Raw output from DPU (shape [1, 13, 13, 75]).
        frame (np.ndarray): Original frame to draw boxes on.
        conf_threshold (float): Minimum confidence to display detection
        nms_threshold (float): Threshold for Non-Maximum Suppression (NMS)

    Returns:
        np.ndarray: Frame with bounding boxes drawn

    Steps:
        1. Reshape the output to (grid_h, grid_w, anchors, attributes)
        2. Convert model outputs to absolute bounding boxes
        3. Apply confidence thresholding
        4. Apply Non-Maximum Suppression to remove duplicates
        5. Draw bounding boxes and labels
    """
    H, W = frame.shape[:2]

    # YOLOv3 VOC predefined anchors (first scale, for 13x13 grid)
    anchors = [(116, 90), (156, 198), (373, 326)]
    grid_size = 13
    num_anchors = 3
    num_classes = 20

    # Reshape output to [grid_h, grid_w, anchors, 5+num_classes]
    output = output.reshape(grid_size, grid_size, num_anchors, 5 + num_classes)

    boxes = []
    confidences = []
    class_ids = []

    # Iterate through all grid cells and anchors
    for row in range(grid_size):
        for col in range(grid_size):
            for a in range(num_anchors):
                tx, ty, tw, th, obj_score = output[row, col, a, :5]
                obj_score = sigmoid(obj_score)  # Objectness probability

                if obj_score < conf_threshold:
                    continue  # Skip low-confidence boxes

                # Compute bounding box center coordinates
                bx = (sigmoid(tx) + col) / grid_size
                by = (sigmoid(ty) + row) / grid_size
                # Compute width and height relative to anchors
                bw = np.exp(tw) * anchors[a][0] / 416
                bh = np.exp(th) * anchors[a][1] / 416

                # Convert normalized coordinates to pixel coordinates
                x = int((bx - bw / 2) * W)
                y = int((by - bh / 2) * H)
                w = int(bw * W)
                h = int(bh * H)

                # Determine class ID and confidence
                class_probs = sigmoid(output[row, col, a, 5:])
                class_id = np.argmax(class_probs)
                confidence = obj_score * class_probs[class_id]

                if confidence > conf_threshold:
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

    # Apply Non-Maximum Suppression to remove overlapping boxes
    indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

    # Draw bounding boxes and labels
    if len(indices) > 0:
        for i in indices.flatten():
            x, y, w, h = boxes[i]
            label = CLASS_NAMES[class_ids[i]]
            conf = confidences[i]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    person_detected = any(CLASS_NAMES[class_ids[i]] == "person" for i in indices.flatten()) if len(indices) > 0 else False
    return frame, person_detected


# ------------------- YOLO DPU THREAD ------------------- #
class YoloDpuThread(threading.Thread):
    def __init__(self, device_id: str = "camera0", camera_index: int = 0):
        super().__init__(daemon=True)
        self.device_id = device_id
        self.camera_index = camera_index

        self.stop_event = threading.Event()
        self.active_event = threading.Event()

        self.cap = None
        self.runner = None

        self.result_lock = threading.Lock()
        self.latest_result = None
        self.latest_result_ts = None

        self.no_person_timeout_sec = 3.0
        self._last_person_seen_ts = None

    def activate(self):
        self.active_event.set()

    def deactivate(self):
        self.active_event.clear()
        self._last_person_seen_ts = None
        with self.result_lock:
            self.latest_result = None
            self.latest_result_ts = None

    def get_latest_result(self):
        with self.result_lock:
            return self.latest_result, self.latest_result_ts

    def run(self):
        """
        Load the compiled DPU model and perform real-time object detection.

        Args:
        """
        model_path = get_dpu_path()

        # Load the model graph
        graph = xir.Graph.deserialize(model_path)

        # Find the subgraph that runs on the DPU
        dpu_subgraph = [sg for sg in graph.get_root_subgraph().toposort_child_subgraph()
                        if sg.has_attr("device") and sg.get_attr("device").upper() == "DPU"][0]

        # Create a DPU runner for inference
        self.runner = vart.Runner.create_runner(dpu_subgraph, "run")

        # Get input and output tensor information
        input_tensors = self.runner.get_input_tensors()
        output_tensors = self.runner.get_output_tensors()
        input_shape = tuple(input_tensors[0].dims)

        # Open webcam only if active event is set (IMU detection)
        while not self.stop_event.is_set():
            if not self.active_event.wait(timeout=0.5):
                continue

            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                from utils.logger import log_system
                log_system("[YoloDpuThread] Webcam not found", level="ERROR")
                self.active_event.clear()
                continue

            # Set webcam resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Prepare empty output buffers for the DPU
            output_data = [np.empty(tuple(ot.dims), dtype=np.float32) for ot in output_tensors]

            self._last_person_seen_ts = time.monotonic()

            while self.active_event.is_set() and not self.stop_event.is_set():
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Preprocess the frame for DPU input
                img_input = preprocess(frame, input_shape)

                # Run inference on DPU
                job_id = self.runner.execute_async([img_input], output_data)
                self.runner.wait(job_id)

                # Postprocess the output to draw bounding boxes
                frame, person_detected = postprocess(output_data[0], frame)

                now = time.monotonic()

                if person_detected:
                    self._last_person_seen_ts = now
                else:
                    if self._last_person_seen_ts is not None and (
                            now - self._last_person_seen_ts) >= self.no_person_timeout_sec:
                        self.deactivate()
                        break

                with self.result_lock:
                    self.latest_result = person_detected
                    self.latest_result_ts = time.monotonic()

                # Show the frame
                cv2.imshow("YOLOv3 DPU", frame)

                # Exit loop
                cv2.waitKey(1)

            # Release resources
            if self.cap:
                self.cap.release()
                self.cap = None

            cv2.destroyAllWindows()

        self.runner = None

    def stop(self):
        self.stop_event.set()
        self.active_event.set()
        if self.is_alive():
            self.join()
