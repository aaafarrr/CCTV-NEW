import os
import json
import time
import logging
import threading
from collections import deque
import numpy as np
import cv2
from typing import Dict, Any, Optional, List, Tuple
from app.services.ai.detector import detector_tracker
from app.services.ai.counting import counting_engine
from app.services.ai.anomaly import anomaly_engine
from app.services.ai.face_engine import face_engine

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;5000000"

logger = logging.getLogger("cctv_new.camera_stream")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
CAMERAS_JSON_PATH = os.path.join(STORAGE_DIR, "cameras.json")

SYNTHETIC_MODES = {"synthetic_lobby", "synthetic_parking", "synthetic_gate", "synthetic_warehouse", ""}

class CameraStreamManager:
    """
    Manages active camera streams (RTSP, ONVIF, V380, Synthetic AI Simulator).
    Includes ZoneMinder-style Pre-Alarm Circular Frame Buffer & Real-time PTZ / Digital Zoom processor.
    """
    def __init__(self):
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.ptz_states: Dict[str, Dict[str, float]] = {}
        self.pre_event_buffers: Dict[str, deque] = {}
        self.timeline_bands: Dict[str, List[Dict[str, Any]]] = {}
        self.recent_runtime_alerts: deque = deque(maxlen=40)
        self.is_running = True
        self._load_persistent_cameras()

    def stop_all(self):
        self.is_running = False
        for _, stream_data in list(self.active_streams.items()):
            stream_data["stopped"] = True
            cap = stream_data.get("cap")
            if cap:
                try:
                    cap.release()
                except Exception:
                    pass
                stream_data["cap"] = None

    def _default_cameras(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "cam_1",
                "name": "Kamera Utama (Lobby)",
                "location": "Lantai 1 - Pintu Masuk Utama",
                "stream_url": "synthetic_lobby",
                "enable_counting": True,
                "enable_suspicious": True,
                "enable_face_rec": True,
                "roi_zones": [
                    {
                        "id": "z_vault_1",
                        "name": "Area Resepsionis & Kasir",
                        "type": "INTRUSION",
                        "polygon": [{"x": 420, "y": 190}, {"x": 610, "y": 190}, {"x": 610, "y": 350}, {"x": 420, "y": 350}],
                        "max_dwell_sec": 5
                    }
                ],
                "counting_lines": [
                    {
                        "id": "l_lobby_1",
                        "name": "Garis Pintu Lobby",
                        "start": {"x": 40, "y": 270},
                        "end": {"x": 400, "y": 270}
                    }
                ]
            },
            {
                "id": "cam_2",
                "name": "Kamera Area Parkir",
                "location": "Gedung B - Parkir Kendaraan",
                "stream_url": "synthetic_parking",
                "enable_counting": True,
                "enable_suspicious": True,
                "enable_face_rec": False,
                "roi_zones": [
                    {
                        "id": "z_park_1",
                        "name": "Jalur Evakuasi Darurat",
                        "type": "LOITERING",
                        "polygon": [{"x": 60, "y": 200}, {"x": 250, "y": 200}, {"x": 250, "y": 330}, {"x": 60, "y": 330}],
                        "max_dwell_sec": 6
                    }
                ],
                "counting_lines": [
                    {
                        "id": "l_park_1",
                        "name": "Portal Masuk Parkir",
                        "start": {"x": 50, "y": 360},
                        "end": {"x": 590, "y": 360}
                    }
                ]
            },
            {
                "id": "cam_3",
                "name": "Kamera Gerbang Kargo (V380)",
                "location": "Sektor Timur - Loading Dock",
                "stream_url": "synthetic_gate",
                "enable_counting": True,
                "enable_suspicious": True,
                "enable_face_rec": True,
                "roi_zones": [],
                "counting_lines": [
                    {
                        "id": "l_gate_1",
                        "name": "Gerbang Logistik",
                        "start": {"x": 60, "y": 300},
                        "end": {"x": 580, "y": 300}
                    }
                ]
            },
            {
                "id": "cam_4",
                "name": "Kamera Gudang & Brankas",
                "location": "Lantai B1 - Ruang Vault",
                "stream_url": "synthetic_warehouse",
                "enable_counting": True,
                "enable_suspicious": True,
                "enable_face_rec": True,
                "roi_zones": [
                    {
                        "id": "z_vault_secure",
                        "name": "Zona Brankas Utama",
                        "type": "INTRUSION",
                        "polygon": [{"x": 180, "y": 160}, {"x": 460, "y": 160}, {"x": 460, "y": 360}, {"x": 180, "y": 360}],
                        "max_dwell_sec": 3
                    }
                ],
                "counting_lines": []
            }
        ]

    def _load_persistent_cameras(self):
        os.makedirs(STORAGE_DIR, exist_ok=True)
        if not os.path.exists(CAMERAS_JSON_PATH):
            for cam_info in self._default_cameras():
                self.add_or_update_camera(cam_info, save_to_disk=False)
            self._save_persistent_cameras()
            return

        try:
            with open(CAMERAS_JSON_PATH, "r", encoding="utf-8") as f:
                cams_data = json.load(f)
                if not cams_data:
                    cams_data = self._default_cameras()
                for cam_info in cams_data:
                    self.add_or_update_camera(cam_info, save_to_disk=False)
        except Exception as e:
            logger.error(f"Error loading cameras.json: {e}")
            for cam_info in self._default_cameras():
                self.add_or_update_camera(cam_info, save_to_disk=False)

    def _save_persistent_cameras(self):
        os.makedirs(STORAGE_DIR, exist_ok=True)
        cams_data = [data["info"] for data in self.active_streams.values()]
        try:
            with open(CAMERAS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(cams_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cameras.json: {e}")

    def _init_timeline_bands(self, camera_id: str):
        now = time.time()
        self.timeline_bands[camera_id] = [
            {"id": f"{camera_id}_ev1", "hour_offset": -6.5, "duration_min": 14, "type": "PERSON", "color": "#06b6d4", "label": "Aktivitas Pedestrian Pagi", "timestamp": now - 6.5 * 3600},
            {"id": f"{camera_id}_ev2", "hour_offset": -4.2, "duration_min": 18, "type": "VEHICLE", "color": "#8b5cf6", "label": "Konvoi Kendaraan Masuk", "timestamp": now - 4.2 * 3600},
            {"id": f"{camera_id}_ev3", "hour_offset": -2.1, "duration_min": 8, "type": "LOITERING", "color": "#f59e0b", "label": "Peringatan Loitering Area Terbatas", "timestamp": now - 2.1 * 3600},
            {"id": f"{camera_id}_ev4", "hour_offset": -0.6, "duration_min": 6, "type": "INTRUSION", "color": "#ef4444", "label": "Pelanggaran Perimeter / Watchlist", "timestamp": now - 0.6 * 3600},
        ]

    def add_or_update_camera(self, cam_info: Dict[str, Any], save_to_disk: bool = True):
        cam_id = cam_info["id"]
        stream_url = cam_info.get("stream_url", "")

        if cam_id in self.active_streams:
            self.active_streams[cam_id]["stopped"] = True
            if self.active_streams[cam_id].get("cap"):
                try:
                    self.active_streams[cam_id]["cap"].release()
                except Exception:
                    pass

        self.ptz_states.setdefault(cam_id, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0})
        self.pre_event_buffers.setdefault(cam_id, deque(maxlen=75))  # ~5s circular buffer
        if cam_id not in self.timeline_bands:
            self._init_timeline_bands(cam_id)

        self.active_streams[cam_id] = {
            "info": cam_info,
            "cap": None,
            "is_connecting": True if stream_url and stream_url not in SYNTHETIC_MODES else False,
            "last_connect_attempt": 0.0,
            "consecutive_failures": 0,
            "latest_frame": None,
            "latest_jpeg_boxes": None,
            "latest_jpeg_clean": None,
            "stopped": False,
            "latest_metadata": {
                "people_count": 0,
                "vehicle_count": 0,
                "motion_energy": 0.0,
                "detected_faces": [],
                "alerts": []
            }
        }

        if save_to_disk:
            self._save_persistent_cameras()

        t = threading.Thread(target=self._camera_worker_loop, args=(cam_id,), daemon=True)
        t.start()

    def control_ptz(self, camera_id: str, action: str, step: float = 0.15) -> Dict[str, float]:
        state = self.ptz_states.setdefault(camera_id, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0})
        if action == "zoom_in":
            state["zoom"] = round(min(3.0, state["zoom"] + 0.25), 2)
        elif action == "zoom_out":
            state["zoom"] = round(max(1.0, state["zoom"] - 0.25), 2)
        elif action == "pan_left":
            state["pan"] = round(max(-1.0, state["pan"] - step), 2)
        elif action == "pan_right":
            state["pan"] = round(min(1.0, state["pan"] + step), 2)
        elif action == "tilt_up":
            state["tilt"] = round(max(-1.0, state["tilt"] - step), 2)
        elif action == "tilt_down":
            state["tilt"] = round(min(1.0, state["tilt"] + step), 2)
        elif action == "reset":
            state["pan"] = 0.0
            state["tilt"] = 0.0
            state["zoom"] = 1.0
        return state

    def _apply_ptz_transform(self, camera_id: str, frame: np.ndarray) -> np.ndarray:
        state = self.ptz_states.get(camera_id, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0})
        zoom = float(state.get("zoom", 1.0))
        pan = float(state.get("pan", 0.0))
        tilt = float(state.get("tilt", 0.0))
        if zoom <= 1.01 and abs(pan) < 0.01 and abs(tilt) < 0.01:
            return frame

        h, w = frame.shape[:2]
        eff_zoom = max(1.0, zoom)
        crop_w = int(w / eff_zoom)
        crop_h = int(h / eff_zoom)

        max_dx = max(0, (w - crop_w) // 2)
        max_dy = max(0, (h - crop_h) // 2)

        cx = w // 2 + int(pan * max_dx)
        cy = h // 2 + int(tilt * max_dy)

        x1 = max(0, min(w - crop_w, cx - crop_w // 2))
        y1 = max(0, min(h - crop_h, cy - crop_h // 2))
        cropped = frame[y1:y1 + crop_h, x1:x1 + crop_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    def _camera_worker_loop(self, camera_id: str):
        while self.is_running:
            if camera_id not in self.active_streams:
                break
            stream_data = self.active_streams[camera_id]
            if stream_data.get("stopped"):
                break

            cam_info = stream_data["info"]
            stream_url = cam_info.get("stream_url", "")
            now = time.time()

            cap = stream_data.get("cap")
            if cap is None and stream_url and stream_url not in SYNTHETIC_MODES:
                last_attempt = stream_data.get("last_connect_attempt", 0.0)
                if now - last_attempt >= 5.0:
                    stream_data["last_connect_attempt"] = now
                    try:
                        cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                        if cap and cap.isOpened():
                            stream_data["cap"] = cap
                            stream_data["is_connecting"] = False
                            stream_data["consecutive_failures"] = 0
                        else:
                            if cap:
                                cap.release()
                            cap = None
                    except Exception:
                        cap = None

            frame = None
            if cap and cap.isOpened():
                ret, read_frame = cap.read()
                if ret and read_frame is not None and read_frame.size > 0:
                    frame = read_frame
                    stream_data["consecutive_failures"] = 0
                else:
                    failures = stream_data.get("consecutive_failures", 0) + 1
                    stream_data["consecutive_failures"] = failures
                    if failures >= 30:
                        try:
                            cap.release()
                        except Exception:
                            pass
                        stream_data["cap"] = None
                        stream_data["is_connecting"] = True
                        stream_data["consecutive_failures"] = 0

            if frame is None:
                if stream_url in SYNTHETIC_MODES:
                    frame = self._generate_synthetic_frame(camera_id, stream_url)
                else:
                    frame = self._generate_standby_frame(camera_id)

            frame = self._apply_ptz_transform(camera_id, frame)
            self.pre_event_buffers[camera_id].append(frame)

            try:
                annotated_boxes, annotated_clean, metadata = self.process_frame_dual(camera_id, frame)
                ret_b, buf_boxes = cv2.imencode(".jpg", annotated_boxes, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if ret_b:
                    stream_data["latest_jpeg_boxes"] = buf_boxes.tobytes()

                ret_c, buf_clean = cv2.imencode(".jpg", annotated_clean, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if ret_c:
                    stream_data["latest_jpeg_clean"] = buf_clean.tobytes()

                stream_data["latest_frame"] = annotated_boxes
                stream_data["latest_metadata"] = metadata
            except Exception as e:
                logger.error(f"Error in background worker for {camera_id}: {e}")

            time.sleep(0.06)

    def get_latest_frame_jpeg(self, camera_id: str, show_boxes: bool = True) -> Optional[bytes]:
        if camera_id not in self.active_streams:
            return None
        stream_data = self.active_streams[camera_id]
        jpeg = (
            stream_data.get("latest_jpeg_boxes") if show_boxes else stream_data.get("latest_jpeg_clean")
        ) or stream_data.get("latest_jpeg_boxes")

        if jpeg is None:
            standby_frame = self._generate_standby_frame(camera_id)
            ret, buf = cv2.imencode(".jpg", standby_frame)
            return buf.tobytes() if ret else None
        return jpeg

    def process_frame_dual(self, camera_id: str, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        cam_info = self.active_streams[camera_id]["info"]
        clean_frame = frame.copy()
        box_frame = frame.copy()

        # 1. Motion Pre-Filter & Object Detection
        box_frame, detections = detector_tracker.process_frame(box_frame, camera_id, draw_boxes=True)

        # 2. Traffic Counting
        counts = {"people_in": 0, "people_out": 0, "vehicles_in": 0, "vehicles_out": 0}
        if cam_info.get("enable_counting"):
            counts = counting_engine.process_counting(
                camera_id,
                detections,
                cam_info.get("counting_lines", [])
            )

        # 3. Behavior & Anomaly Detection
        alerts = []
        if cam_info.get("enable_suspicious"):
            alerts = anomaly_engine.analyze_behavior(
                camera_id,
                cam_info.get("name", camera_id),
                detections,
                cam_info.get("roi_zones", [])
            )
            for al in alerts:
                self.recent_runtime_alerts.appendleft({
                    "id": f"rt_{int(time.time()*1000)}_{camera_id}",
                    "timestamp": time.time(),
                    **al
                })

        # 4. Face Recognition
        faces = []
        if cam_info.get("enable_face_rec"):
            faces = face_engine.extract_faces_from_frame(
                box_frame,
                camera_id,
                cam_info.get("name", camera_id),
                draw_boxes=True
            )

        # Draw ROI Zones & Counting Lines on box_frame
        self._draw_zones_and_lines(box_frame, cam_info)

        # Draw OSD HUD on both frames
        self._draw_cctv_hud(box_frame, camera_id, cam_info.get("name", camera_id), counts, alerts)
        self._draw_cctv_hud(clean_frame, camera_id, cam_info.get("name", camera_id), counts, [])

        metadata = {
            "camera_id": camera_id,
            "people_count": sum(1 for d in detections if d["class_name"] == "person"),
            "vehicle_count": sum(1 for d in detections if d["class_name"] != "person"),
            "motion_energy": detector_tracker.motion_energy.get(camera_id, 0.0),
            "traffic_counts": counts,
            "detected_faces": faces,
            "alerts": alerts,
            "ptz": self.ptz_states.get(camera_id, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0}),
            "timestamp": time.time()
        }
        return box_frame, clean_frame, metadata

    def _draw_zones_and_lines(self, frame: np.ndarray, cam_info: Dict[str, Any]):
        for zone in cam_info.get("roi_zones", []):
            poly = zone.get("polygon", [])
            if len(poly) >= 3:
                pts = np.array([[int(p.get("x", 0)), int(p.get("y", 0))] for p in poly], np.int32)
                is_intrusion = zone.get("type", "INTRUSION") == "INTRUSION"
                # Red #ef4444 (BGR 68,68,239) for Intrusion, Amber #f59e0b (BGR 11,158,245) for Loitering
                color = (68, 68, 239) if is_intrusion else (11, 158, 245)
                overlay = frame.copy()
                cv2.fillPoly(overlay, [pts], color)
                cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
                cv2.polylines(frame, [pts], True, color, 2)
                p0 = pts[0]
                cv2.putText(frame, f"ZONE: {zone.get('name', 'ROI')}", (p0[0] + 6, p0[1] + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)

        for line in cam_info.get("counting_lines", []):
            s = line.get("start", {"x": 40, "y": 270})
            e = line.get("end", {"x": 580, "y": 270})
            p1 = (int(s.get("x", 40)), int(s.get("y", 270)))
            p2 = (int(e.get("x", 580)), int(e.get("y", 270)))
            # Cyan #06b6d4 (BGR 212, 182, 6)
            cv2.line(frame, p1, p2, (212, 182, 6), 2)
            cv2.putText(frame, f"LINE: {line.get('name', 'Counter')}", (p1[0] + 6, max(20, p1[1] - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (212, 182, 6), 1)

    def _draw_cctv_hud(self, frame: np.ndarray, camera_id: str, cam_name: str, counts: Dict[str, int], alerts: List[Dict[str, Any]]):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 38), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)

        # Online dot + Camera Name
        cv2.circle(frame, (16, 19), 5, (129, 185, 16), -1)
        cv2.putText(frame, f"REC | {cam_name}", (28, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)

        ptz = self.ptz_states.get(camera_id, {"zoom": 1.0})
        zoom_str = f"PTZ {ptz.get('zoom', 1.0):.1f}x"
        hud_text = f"IN:{counts.get('people_in', 0)}P / {counts.get('vehicles_in', 0)}V | {zoom_str} | {time.strftime('%H:%M:%S')}"
        cv2.putText(frame, hud_text, (w - 310, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (226, 232, 240), 1)

        if alerts:
            alert = alerts[0]
            cv2.rectangle(frame, (0, h - 34), (w, h), (45, 45, 220), -1)
            cv2.putText(frame, f"ALERT: {alert['description'][:68]}", (12, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1)

    def _generate_standby_frame(self, camera_id: str) -> np.ndarray:
        h, w = 420, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = [18, 24, 36]
        for x in range(0, w, 80):
            cv2.line(frame, (x, 0), (x, h), (30, 41, 59), 1)
        for y in range(0, h, 60):
            cv2.line(frame, (0, y), (w, y), (30, 41, 59), 1)
        cv2.putText(frame, f"CAMERA [{camera_id.upper()}] STANDBY - CONNECTING...", (105, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 160, 40), 2)
        return frame

    def _generate_synthetic_frame(self, camera_id: str, mode: str) -> np.ndarray:
        h, w = 420, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        t = time.time() * 1.8

        if mode == "synthetic_parking":
            frame[:] = [32, 38, 46]
            cv2.rectangle(frame, (0, 170), (w, h), (44, 52, 64), -1)
            for x in range(80, w, 120):
                cv2.line(frame, (x, 170), (x - 30, h), (180, 190, 200), 1)
            # Moving Car 1
            v1_x = int(w - ((t * 75) % (w + 140)))
            cv2.rectangle(frame, (v1_x, 325), (v1_x + 92, 370), (235, 110, 50), -1)
            # Moving Person
            p1_x = int((t * 42) % (w + 80)) - 40
            cv2.circle(frame, (p1_x, 235), 11, (129, 185, 16), -1)
            cv2.rectangle(frame, (p1_x - 10, 246), (p1_x + 10, 282), (129, 185, 16), -1)

        elif mode == "synthetic_gate":
            frame[:] = [28, 36, 42]
            cv2.rectangle(frame, (0, 200), (w, h), (48, 56, 62), -1)
            cv2.line(frame, (0, 300), (w, 300), (80, 180, 250), 1)
            # Cargo Truck moving vertically/diagonally
            trk_x = int((t * 60) % (w + 180)) - 90
            cv2.rectangle(frame, (trk_x, 260), (trk_x + 115, 318), (80, 140, 240), -1)
            # Worker walking
            p2_x = int(w - ((t * 38) % (w + 60)))
            cv2.circle(frame, (p2_x, 220), 11, (50, 210, 120), -1)
            cv2.rectangle(frame, (p2_x - 9, 231), (p2_x + 9, 268), (50, 210, 120), -1)

        elif mode == "synthetic_warehouse":
            frame[:] = [24, 30, 38]
            cv2.rectangle(frame, (40, 80), (140, 360), (50, 60, 75), -1)
            cv2.rectangle(frame, (500, 80), (600, 360), (50, 60, 75), -1)
            # Patrol / Intruder moving across vault zone
            px = int(160 + 150 * (0.5 + 0.5 * np.sin(t * 0.7)))
            py = int(230 + 45 * np.cos(t * 0.9))
            cv2.circle(frame, (px, py), 12, (90, 200, 255), -1)
            cv2.rectangle(frame, (px - 11, py + 12), (px + 11, py + 48), (90, 200, 255), -1)

        else:  # synthetic_lobby
            frame[:] = [34, 42, 54]
            cv2.rectangle(frame, (0, 210), (w, h), (52, 62, 76), -1)
            # Reception desk on right
            cv2.rectangle(frame, (430, 200), (595, 340), (70, 82, 98), 2)
            # Person 1 crossing lobby line
            p1_x = int(90 + 180 * (0.5 + 0.5 * np.sin(t * 0.65)))
            p1_y = int(265 + 65 * np.sin(t * 0.85))
            cv2.circle(frame, (p1_x, p1_y), 12, (129, 185, 16), -1)
            cv2.rectangle(frame, (p1_x - 11, p1_y + 12), (p1_x + 11, p1_y + 46), (129, 185, 16), -1)
            # Person 2 approaching reception
            p2_x = int(360 + 120 * (0.5 + 0.5 * np.cos(t * 0.5)))
            p2_y = int(245 + 30 * np.sin(t * 0.6))
            cv2.circle(frame, (p2_x, p2_y), 12, (240, 175, 60), -1)
            cv2.rectangle(frame, (p2_x - 11, p2_y + 12), (p2_x + 11, p2_y + 46), (240, 175, 60), -1)

        return frame

    def update_camera_config(
        self,
        camera_id: str,
        name: str,
        location: str,
        stream_url: str,
        enable_counting: bool,
        enable_suspicious: bool,
        enable_face_rec: bool,
        roi_zones: List[Dict[str, Any]],
        counting_lines: List[Dict[str, Any]]
    ):
        if camera_id in self.active_streams:
            cam_info = self.active_streams[camera_id]["info"]
            cam_info["name"] = name
            cam_info["location"] = location
            cam_info["stream_url"] = stream_url
            cam_info["enable_counting"] = enable_counting
            cam_info["enable_suspicious"] = enable_suspicious
            cam_info["enable_face_rec"] = enable_face_rec
            cam_info["roi_zones"] = roi_zones
            cam_info["counting_lines"] = counting_lines
            self._save_persistent_cameras()

stream_manager = CameraStreamManager()
