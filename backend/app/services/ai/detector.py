import logging
import numpy as np
import cv2
from typing import List, Dict, Any, Tuple
from app.core.config import settings

logger = logging.getLogger("cctv_new.ai.detector")

# COCO classes of primary interest for CCTV
TARGET_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

class RealObjectDetectorTracker:
    """
    Production-grade object detector and tracker using YOLOv8n (Ultralytics)
    combined with a fast background motion pre-filter to save CPU when scenes are idle.
    """
    def __init__(self):
        self.model = None
        self.device = settings.AI_DEVICE
        self.conf_threshold = settings.YOLO_CONFIDENCE
        self.motion_energy: Dict[str, float] = {}
        self.bg_subtractors: Dict[str, Any] = {}
        self.next_track_id: Dict[str, int] = {}
        self.prev_tracks: Dict[str, Dict[int, List[int]]] = {}
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLOv8 model: {settings.YOLO_MODEL} on device: {self.device}")
            self.model = YOLO(settings.YOLO_MODEL)
            # Warm up on CPU/Device
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            self.model(dummy, verbose=False, device=self.device)
            logger.info("YOLOv8 model initialized and ready.")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            self.model = None

    def _get_bg_subtractor(self, camera_id: str):
        if camera_id not in self.bg_subtractors:
            self.bg_subtractors[camera_id] = cv2.createBackgroundSubtractorMOG2(
                history=300, varThreshold=30, detectShadows=False
            )
            self.prev_tracks[camera_id] = {}
            self.next_track_id[camera_id] = 101
        return self.bg_subtractors[camera_id]

    def _match_track_id(self, camera_id: str, center: List[int]) -> int:
        tracks = self.prev_tracks.setdefault(camera_id, {})
        best_id = None
        best_dist = 60.0
        for tid, prev_c in tracks.items():
            dist = float(np.hypot(center[0] - prev_c[0], center[1] - prev_c[1]))
            if dist < best_dist:
                best_dist = dist
                best_id = tid
        if best_id is None:
            best_id = self.next_track_id.get(camera_id, 101)
            self.next_track_id[camera_id] = (best_id % 9000) + 101
        return best_id

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str,
        draw_boxes: bool = True,
        force_infer: bool = False
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        detections: List[Dict[str, Any]] = []
        if self.model is None or frame is None or frame.size == 0:
            return frame, detections

        # 1. Motion Pre-Filter (Motion Gating)
        subtractor = self._get_bg_subtractor(camera_id)
        small_frame = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_NEAREST)
        fg_mask = subtractor.apply(small_frame)
        changed_ratio = float(np.count_nonzero(fg_mask)) / float(fg_mask.size)
        self.motion_energy[camera_id] = round(changed_ratio * 100, 2)

        # Skip inference if static and not forced
        if not force_infer and changed_ratio < 0.002:
            return frame, detections

        # 2. YOLOv8 Inference
        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
                classes=list(TARGET_CLASSES.keys())
            )
        except Exception as e:
            logger.error(f"YOLO predict error on camera {camera_id}: {e}")
            return frame, detections

        new_tracks: Dict[int, List[int]] = {}

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                if cls_id not in TARGET_CLASSES:
                    continue
                class_name = TARGET_CLASSES[cls_id]
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = xyxy

                center = [(x1 + x2) // 2, (y1 + y2) // 2]
                track_id = self._match_track_id(camera_id, center)
                new_tracks[track_id] = center

                detections.append({
                    "id": track_id,
                    "class_name": class_name,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": round(conf, 2),
                    "center": center
                })

                if draw_boxes:
                    # UI theme standard colors: Emerald #10b981 for Person, Purple #8b5cf6 for Vehicle
                    color = (129, 185, 16) if class_name == "person" else (246, 92, 139)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"#{track_id} {class_name.upper()} {int(conf * 100)}%"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(frame, (x1, max(0, y1 - th - 8)), (x1 + tw + 8, max(th + 8, y1)), color, -1)
                    cv2.putText(frame, label, (x1 + 4, max(14, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        self.prev_tracks[camera_id] = new_tracks
        return frame, detections

detector_tracker = RealObjectDetectorTracker()
