import os
import json
import time
import sqlite3
import logging
import threading
from datetime import datetime
from collections import deque
import numpy as np
import cv2
from typing import Dict, Any, Optional, List, Tuple
from app.core.config import settings
from app.services.ai.detector import detector_tracker
from app.services.ai.counting import counting_engine
from app.services.ai.anomaly import anomaly_engine
from app.services.ai.face_engine import face_engine
from app.services.storage_gateway import storage_gateway

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;5000000"

logger = logging.getLogger("cctv_new.camera_stream")

CAMERAS_JSON_PATH = os.path.join(settings.STORAGE_DIR, "cameras.json")

class CameraStreamManager:
    """
    Production-ready Stream Manager supporting RTSP, ONVIF, and HTTP IP Cameras.
    Provides background capture, ring-buffer for pre-alarm replay, and AI pipeline.
    Starts with 0 cameras until configured by the administrator.
    """
    def __init__(self):
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.ptz_states: Dict[str, Dict[str, float]] = {}
        self.pre_event_buffers: Dict[str, deque] = {}
        self.timeline_bands: Dict[str, List[Dict[str, Any]]] = {}
        self.recent_runtime_alerts: deque = deque(maxlen=50)
        self.last_cloud_sync_ts: Dict[str, float] = {}
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

    def _load_persistent_cameras(self):
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        if not os.path.exists(CAMERAS_JSON_PATH):
            # Production: Empty camera list by default
            with open(CAMERAS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            return

        try:
            with open(CAMERAS_JSON_PATH, "r", encoding="utf-8") as f:
                cams_data = json.load(f)
                for cam_info in cams_data:
                    self.add_or_update_camera(cam_info, save_to_disk=False)
        except Exception as e:
            logger.error(f"Error loading cameras.json: {e}")

    def _save_persistent_cameras(self):
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        cams_data = [data["info"] for data in self.active_streams.values()]
        try:
            with open(CAMERAS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(cams_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cameras.json: {e}")

    def add_or_update_camera(self, cam_info: Dict[str, Any], save_to_disk: bool = True):
        cam_id = cam_info["id"]

        if cam_id in self.active_streams:
            self.active_streams[cam_id]["stopped"] = True
            if self.active_streams[cam_id].get("cap"):
                try:
                    self.active_streams[cam_id]["cap"].release()
                except Exception:
                    pass

        self.ptz_states.setdefault(cam_id, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0})
        self.pre_event_buffers.setdefault(cam_id, deque(maxlen=75))  # ~5 seconds pre-event buffer
        self.timeline_bands.setdefault(cam_id, [])

        self.active_streams[cam_id] = {
            "info": cam_info,
            "cap": None,
            "is_connecting": True,
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
        infer_counter = 0
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
            if cap is None and stream_url:
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
                    except Exception as e:
                        logger.debug(f"Connection failure to {stream_url}: {e}")
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
                    if failures >= 25:
                        try:
                            cap.release()
                        except Exception:
                            pass
                        stream_data["cap"] = None
                        stream_data["is_connecting"] = True
                        stream_data["consecutive_failures"] = 0

            if frame is None:
                frame = self._generate_offline_frame(camera_id, cam_info.get("name", camera_id))
                ret, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if ret:
                    b_bytes = buf.tobytes()
                    stream_data["latest_jpeg_boxes"] = b_bytes
                    stream_data["latest_jpeg_clean"] = b_bytes
                    stream_data["latest_frame"] = frame
                time.sleep(0.5)
                continue

            # Limit resolution for CPU efficiency if needed
            h, w = frame.shape[:2]
            if w > settings.MAX_FRAME_WIDTH:
                new_h = int(h * (settings.MAX_FRAME_WIDTH / w))
                frame = cv2.resize(frame, (settings.MAX_FRAME_WIDTH, new_h), interpolation=cv2.INTER_AREA)

            frame = self._apply_ptz_transform(camera_id, frame)
            self.pre_event_buffers[camera_id].append(frame)

            infer_counter += 1
            run_ai = (infer_counter % settings.DETECT_EVERY_N_FRAMES == 0)

            try:
                annotated_boxes, annotated_clean, metadata = self.process_frame_dual(
                    camera_id, frame, run_ai=run_ai
                )
                ret_b, buf_boxes = cv2.imencode(".jpg", annotated_boxes, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if ret_b:
                    stream_data["latest_jpeg_boxes"] = buf_boxes.tobytes()

                ret_c, buf_clean = cv2.imencode(".jpg", annotated_clean, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if ret_c:
                    stream_data["latest_jpeg_clean"] = buf_clean.tobytes()

                stream_data["latest_frame"] = annotated_boxes
                stream_data["latest_metadata"] = metadata
            except Exception as e:
                logger.error(f"Error in stream processing for {camera_id}: {e}")

            time.sleep(0.04)

    def get_latest_frame_jpeg(self, camera_id: str, show_boxes: bool = True) -> Optional[bytes]:
        if camera_id not in self.active_streams:
            return None
        stream_data = self.active_streams[camera_id]
        jpeg = (
            stream_data.get("latest_jpeg_boxes") if show_boxes else stream_data.get("latest_jpeg_clean")
        ) or stream_data.get("latest_jpeg_boxes")

        if jpeg is None:
            name = stream_data.get("info", {}).get("name", camera_id)
            off_frame = self._generate_offline_frame(camera_id, name)
            ret, buf = cv2.imencode(".jpg", off_frame)
            return buf.tobytes() if ret else None
        return jpeg

    def process_frame_dual(
        self,
        camera_id: str,
        frame: np.ndarray,
        run_ai: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        cam_info = self.active_streams[camera_id]["info"]
        clean_frame = frame.copy()
        box_frame = frame.copy()

        detections = []
        if run_ai:
            box_frame, detections = detector_tracker.process_frame(box_frame, camera_id, draw_boxes=True)

        counts = {"people_in": 0, "people_out": 0, "vehicles_in": 0, "vehicles_out": 0}
        if cam_info.get("enable_counting"):
            counts = counting_engine.process_counting(
                camera_id,
                detections,
                cam_info.get("counting_lines", [])
            )

        alerts = []
        if cam_info.get("enable_suspicious") and detections:
            alerts = anomaly_engine.analyze_behavior(
                camera_id,
                cam_info.get("name", camera_id),
                detections,
                cam_info.get("roi_zones", [])
            )
            for al in alerts:
                alert_id = f"evt_{int(time.time()*1000)}_{camera_id}"
                snap_url = self._persist_alert_sqlite(alert_id, al, frame=box_frame)
                self.recent_runtime_alerts.appendleft({
                    "id": alert_id,
                    "timestamp": time.time(),
                    "snapshot_url": snap_url,
                    **al
                })

        faces = []
        if cam_info.get("enable_face_rec") and run_ai:
            faces = face_engine.extract_faces_from_frame(
                box_frame,
                camera_id,
                cam_info.get("name", camera_id),
                draw_boxes=True
            )

        self._draw_zones_and_lines(box_frame, cam_info)
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
            cv2.line(frame, p1, p2, (212, 182, 6), 2)
            cv2.putText(frame, f"LINE: {line.get('name', 'Counter')}", (p1[0] + 6, max(20, p1[1] - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (212, 182, 6), 1)

    def _draw_cctv_hud(self, frame: np.ndarray, camera_id: str, cam_name: str, counts: Dict[str, int], alerts: List[Dict[str, Any]]):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 36), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)

        # Online dot + Camera Name
        cv2.circle(frame, (16, 18), 5, (129, 185, 16), -1)
        cv2.putText(frame, f"LIVE | {cam_name}", (28, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)

        ptz = self.ptz_states.get(camera_id, {"zoom": 1.0})
        zoom_str = f"PTZ {ptz.get('zoom', 1.0):.1f}x"
        hud_text = f"P:{counts.get('people_in', 0)} | V:{counts.get('vehicles_in', 0)} | {zoom_str} | {time.strftime('%H:%M:%S')}"
        cv2.putText(frame, hud_text, (max(200, w - 300), 23), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (226, 232, 240), 1)

        if alerts:
            alert = alerts[0]
            cv2.rectangle(frame, (0, h - 32), (w, h), (45, 45, 220), -1)
            cv2.putText(frame, f"ALERT: {alert['description'][:68]}", (12, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1)

    def _generate_offline_frame(self, camera_id: str, cam_name: str) -> np.ndarray:
        h, w = 360, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = [20, 24, 32]
        # Grid pattern
        for x in range(0, w, 64):
            cv2.line(frame, (x, 0), (x, h), (30, 38, 48), 1)
        for y in range(0, h, 64):
            cv2.line(frame, (0, y), (w, y), (30, 38, 48), 1)
        cv2.circle(frame, (w // 2, h // 2 - 20), 24, (50, 60, 80), -1)
        cv2.putText(frame, "!", (w // 2 - 6, h // 2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (180, 190, 200), 2)
        cv2.putText(frame, f"{cam_name.upper()} (OFFLINE)", (w // 2 - 120, h // 2 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
        cv2.putText(frame, "Menghubungkan ke URL RTSP...", (w // 2 - 95, h // 2 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 150, 160), 1)
        return frame

    def get_pre_event_replay_frames(self, camera_id: str, label: str = "INSIDEN") -> List[bytes]:
        buf = list(self.pre_event_buffers.get(camera_id, []))
        if not buf:
            return []
        total = len(buf)
        encoded_frames: List[bytes] = []
        for idx, raw_frame in enumerate(buf):
            f = raw_frame.copy()
            h, w = f.shape[:2]
            sec_offset = round(((idx - total + 1) / max(1, total)) * 5.0, 1)
            cv2.rectangle(f, (0, 0), (w, 36), (30, 41, 59), -1)
            cv2.circle(f, (18, 18), 6, (68, 68, 239), -1)
            cv2.putText(
                f,
                f"REPLAY PRE-ALARM ({sec_offset:+.1f}s) | {label[:38]}",
                (32, 23),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.46,
                (255, 255, 255),
                1
            )
            ret, jpg = cv2.imencode(".jpg", f, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ret:
                encoded_frames.append(jpg.tobytes())
        return encoded_frames

    def _persist_alert_sqlite(self, alert_id: str, al: Dict[str, Any], frame: Optional[np.ndarray] = None) -> str:
        cam_id = al.get("camera_id", "cam_1")
        cam_name = al.get("camera_name", "Kamera Utama")
        evt_type = al.get("event_type", "INTRUSION")
        sev = al.get("severity", "CRITICAL")

        snap_filename = f"{alert_id}.jpg"
        snap_path = os.path.join(settings.SNAPSHOT_DIR, snap_filename)
        snap_url = f"/media/snapshots/{snap_filename}"

        target_frame = frame if frame is not None else self.active_streams.get(cam_id, {}).get("latest_frame")
        if target_frame is not None:
            try:
                cv2.imwrite(snap_path, target_frame)
            except Exception as e:
                logger.error(f"Failed to write snapshot {snap_path}: {e}")

        # Update Timeline Scrubber
        bands = self.timeline_bands.setdefault(cam_id, [])
        color = "#ef4444" if sev == "CRITICAL" else "#f59e0b"
        bands.append({
            "id": alert_id,
            "hour_offset": -0.05,
            "duration_min": 5,
            "type": "INTRUSION" if evt_type != "LOITERING" else "LOITERING",
            "color": color,
            "label": al.get("description", evt_type)[:48],
            "timestamp": time.time()
        })

        # S3 Cloud Upload if enabled
        now = time.time()
        if (
            storage_gateway.policy.get("auto_sync_critical_events", True)
            and sev == "CRITICAL"
            and now - self.last_cloud_sync_ts.get(cam_id, 0.0) >= 15.0
            and os.path.exists(snap_path)
        ):
            self.last_cloud_sync_ts[cam_id] = now
            storage_gateway.upload_file_to_s3(
                local_path=snap_path,
                remote_filename=f"events/{cam_id}/{snap_filename}",
                metadata={"event_type": evt_type, "camera_id": cam_id}
            )

        if os.path.exists(settings.DATABASE_PATH):
            try:
                with sqlite3.connect(settings.DATABASE_PATH, timeout=2.0) as conn:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO security_events
                        (id, camera_id, camera_name, event_type, severity, description, ai_summary, snapshot_url, cloud_synced, metadata_json, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            alert_id,
                            cam_id,
                            cam_name,
                            evt_type,
                            sev,
                            al.get("description", ""),
                            al.get("ai_summary", ""),
                            snap_url,
                            1 if storage_gateway.s3_client else 0,
                            json.dumps(al.get("metadata", {})),
                            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        )
                    )
                    conn.commit()
            except Exception as e:
                logger.debug(f"SQLite alert persist skipped: {e}")

        return snap_url

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
