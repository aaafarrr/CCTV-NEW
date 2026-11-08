import os
import logging
import numpy as np
import cv2
from typing import List, Dict, Any
from app.core.qdrant_client import vector_service

logger = logging.getLogger("cctv_new.ai.face")

class FaceRecognitionEngine:
    """
    Face Detector & 512-dim Cosine Vector Extractor.
    """
    def __init__(self, device: str = "auto"):
        self.device = device
        self.embedding_size = 512
        self.face_cascade = None

        try:
            if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                if os.path.exists(cascade_path) and hasattr(cv2, "CascadeClassifier"):
                    self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            logger.warning(f"Could not load Haar Cascade: {e}")

    def extract_faces_from_frame(
        self,
        frame: np.ndarray,
        camera_id: str,
        camera_name: str,
        draw_boxes: bool = True
    ) -> List[Dict[str, Any]]:
        detected_faces: List[Dict[str, Any]] = []
        if self.face_cascade is None or self.face_cascade.empty():
            return detected_faces

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            for (x, y, w, h) in faces:
                bbox = [int(x), int(y), int(x + w), int(y + h)]
                face_roi = frame[y:y+h, x:x+w]
                norm_vector = self._extract_vector_from_roi(face_roi)

                matches = vector_service.search_similar_faces(
                    query_vector=norm_vector,
                    limit=3,
                    score_threshold=0.55,
                    camera_id=None
                )

                person_name = "Tamu Baru"
                person_id = f"face_{int(x + y)}"
                score = 0.0
                is_watchlist = False

                if matches:
                    top_match = matches[0]
                    score = top_match.get("score", 0.0)
                    pl = top_match.get("payload", {})
                    person_name = pl.get("person_name", person_name)
                    person_id = pl.get("person_id", person_id)
                    is_watchlist = bool(pl.get("is_watchlist", False))

                detected_faces.append({
                    "bbox": bbox,
                    "confidence": 0.96,
                    "person_id": person_id,
                    "person_name": person_name,
                    "match_score": score,
                    "is_watchlist": is_watchlist
                })

                if draw_boxes:
                    # Red #ef4444 for Watchlist DPO, Blue #3b82f6 for Face Cluster
                    color = (68, 68, 239) if is_watchlist else (246, 130, 59)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(
                        frame,
                        f"FACE: {person_name} ({int(score * 100)}%)",
                        (x, max(20, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2
                    )
        except Exception as ex:
            logger.error(f"Error in face detection: {ex}")

        return detected_faces

    def extract_vector_from_image_bytes(self, image_bytes: bytes) -> List[float]:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Gambar tidak dapat didekode. Pastikan format JPG/PNG valid.")
        return self._extract_vector_from_roi(img)

    def _extract_vector_from_roi(self, img_roi: np.ndarray) -> List[float]:
        resized = cv2.resize(img_roi, (64, 64))
        hist_bgr = cv2.calcHist([resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256]).flatten()
        norm = float(np.linalg.norm(hist_bgr))
        if norm < 1e-6:
            vec = np.ones(512, dtype=np.float32) / np.sqrt(512)
            return vec.tolist()
        normalized_vector = (hist_bgr / norm).astype(np.float32).tolist()
        return normalized_vector

face_engine = FaceRecognitionEngine()

