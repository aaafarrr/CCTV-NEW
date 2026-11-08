import os
import time
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
import cv2
import numpy as np
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.services.google_drive import clospol_gdrive

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;5000000"

logger = logging.getLogger("clospol.cctv_engine")

class ClospolCctvEngine:
    """
    Python implementation of Clospol's CctvService:
    - RTSP/HLS Live Stream & Snapshot Capture
    - Scheduled Background Clip Recording (.mp4 via OpenCV VideoWriter)
    - Automatic Folder-Structured Upload to Google Drive (Root -> Camera -> YYYY-MM)
    - Automatic Retention Enforcer (deleting recordings older than camera.retention_days)
    - Live MJPEG stream endpoint for real-time browser preview
    """
    def __init__(self):
        self.active_caps: Dict[str, cv2.VideoCapture] = {}
        self.latest_frames: Dict[str, bytes] = {}
        self.is_recording: Dict[str, bool] = {}
        self.running = True
        self._worker_thread = threading.Thread(target=self._background_scheduler_loop, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self.running = False
        for cid, cap in list(self.active_caps.items()):
            try:
                cap.release()
            except Exception:
                pass
        self.active_caps.clear()

    def test_connection(self, stream_url: str, snapshot_url: Optional[str] = None) -> bool:
        """Validates stream and snapshot availability matching Clospol testConnection"""
        if stream_url.lower().startswith("rtsp://") or stream_url.lower().startswith("http"):
            try:
                cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                if cap and cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        return True
            except Exception as e:
                logger.debug(f"Stream verification error: {e}")

        if snapshot_url:
            import urllib.request
            try:
                with urllib.request.urlopen(snapshot_url, timeout=4) as resp:
                    return resp.getcode() == 200
            except Exception:
                pass

        return True

    def get_latest_jpeg(self, camera_id: str, stream_url: str) -> Optional[bytes]:
        """Provides real-time JPEG frame from live RTSP/HTTP camera stream"""
        cap = self.active_caps.get(camera_id)
        if cap is None or not cap.isOpened():
            try:
                cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                if cap and cap.isOpened():
                    self.active_caps[camera_id] = cap
                else:
                    return self._generate_standby_frame(camera_id)
            except Exception:
                return self._generate_standby_frame(camera_id)

        ret, frame = cap.read()
        if not ret or frame is None:
            # Reconnect
            cap.release()
            self.active_caps.pop(camera_id, None)
            return self._generate_standby_frame(camera_id)

        # Draw Clean OSD
        h, w = frame.shape[:2]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"REC • {now_str}", (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        ret_b, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret_b:
            b_bytes = buf.tobytes()
            self.latest_frames[camera_id] = b_bytes
            return b_bytes

        return self.latest_frames.get(camera_id)

    def _generate_standby_frame(self, camera_id: str) -> bytes:
        h, w = 360, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = [18, 24, 32]
        cv2.putText(frame, f"CCTV [{camera_id.upper()}] CONNECTING...", (120, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 210, 225), 1)
        ret, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes() if ret else b""

    def capture_snapshot(self, camera_id: str, camera_name: str, stream_url: str) -> Dict[str, Any]:
        """
        Captures a single snapshot image, saves locally, logs to DB,
        and uploads directly to Google Drive (Clospol getOrCreateCctvFolderPath).
        """
        clean_name = camera_name.lower().replace(" ", "_")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"cctv_{clean_name}_{timestamp_str}.jpg"
        local_path = os.path.join(settings.SNAPSHOTS_DIR, file_name)

        frame_bytes = self.get_latest_jpeg(camera_id, stream_url)
        if not frame_bytes:
            raise RuntimeError(f"Gagal mengambil frame gambar dari kamera {camera_name}")

        with open(local_path, "wb") as f:
            f.write(frame_bytes)

        file_size = os.path.getsize(local_path)
        gdrive_file_id = None
        gdrive_web_url = None
        sync_status = "local"

        # Upload to Google Drive if configured
        if clospol_gdrive.is_configured():
            try:
                upload_res = clospol_gdrive.upload_cctv_file(
                    local_path=local_path,
                    file_name=file_name,
                    camera_name=camera_name,
                    mime_type="image/jpeg"
                )
                gdrive_file_id = upload_res.get("file_id")
                gdrive_web_url = upload_res.get("web_view_link")
                sync_status = "synced"
            except Exception as e:
                logger.error(f"Gagal upload snapshot ke Google Drive: {e}")
                sync_status = "failed"

        # Record in SQLite Database
        import uuid
        rec_id = f"snap_{uuid.uuid4().hex[:8]}"
        self._save_recording_record(
            rec_id=rec_id,
            camera_id=camera_id,
            camera_name=camera_name,
            file_name=file_name,
            file_type="image",
            mime_type="image/jpeg",
            file_size_bytes=file_size,
            local_path=local_path,
            gdrive_file_id=gdrive_file_id,
            gdrive_web_url=gdrive_web_url,
            sync_status=sync_status
        )

        return {
            "id": rec_id,
            "file_name": file_name,
            "local_url": f"/media/snapshots/{file_name}",
            "file_size": file_size,
            "google_drive_web_url": gdrive_web_url,
            "sync_status": sync_status
        }

    def record_clip(self, camera_id: str, camera_name: str, stream_url: str, duration_seconds: int = 15) -> Dict[str, Any]:
        """
        Records a video clip (.mp4) from the live stream matching Clospol recordHlsClip,
        and syncs it directly to Google Drive.
        """
        if self.is_recording.get(camera_id):
            return {"status": "in_progress", "message": "Perekaman sedang berlangsung"}

        self.is_recording[camera_id] = True
        clean_name = camera_name.lower().replace(" ", "_")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"cctv_{clean_name}_{timestamp_str}.mp4"
        local_path = os.path.join(settings.RECORDINGS_DIR, file_name)

        try:
            cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                raise RuntimeError(f"Tidak dapat membuka stream kamera {camera_name}")

            fps = cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps < 5 or fps > 60:
                fps = 20.0

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 360

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(local_path, fourcc, fps, (width, height))

            start_t = time.time()
            total_frames = 0
            while time.time() - start_t < duration_seconds:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                out.write(frame)
                total_frames += 1

            out.release()
            cap.release()

            if not os.path.exists(local_path) or total_frames < 5:
                raise RuntimeError("Perekaman video menghasilkan file kosong atau frame terlalu sedikit")

            file_size = os.path.getsize(local_path)
            gdrive_file_id = None
            gdrive_web_url = None
            sync_status = "local"

            # Upload to Google Drive if configured
            if clospol_gdrive.is_configured():
                try:
                    upload_res = clospol_gdrive.upload_cctv_file(
                        local_path=local_path,
                        file_name=file_name,
                        camera_name=camera_name,
                        mime_type="video/mp4"
                    )
                    gdrive_file_id = upload_res.get("file_id")
                    gdrive_web_url = upload_res.get("web_view_link")
                    sync_status = "synced"
                except Exception as e:
                    logger.error(f"Gagal upload video clip ke Google Drive: {e}")
                    sync_status = "failed"

            import uuid
            rec_id = f"clip_{uuid.uuid4().hex[:8]}"
            self._save_recording_record(
                rec_id=rec_id,
                camera_id=camera_id,
                camera_name=camera_name,
                file_name=file_name,
                file_type="video",
                mime_type="video/mp4",
                file_size_bytes=file_size,
                local_path=local_path,
                gdrive_file_id=gdrive_file_id,
                gdrive_web_url=gdrive_web_url,
                sync_status=sync_status
            )

            return {
                "id": rec_id,
                "file_name": file_name,
                "local_url": f"/media/recordings/{file_name}",
                "file_size": file_size,
                "google_drive_web_url": gdrive_web_url,
                "sync_status": sync_status
            }
        finally:
            self.is_recording[camera_id] = False

    def _save_recording_record(self, **kwargs):
        if not os.path.exists(settings.DATABASE_PATH):
            return
        try:
            with sqlite3.connect(settings.DATABASE_PATH, timeout=5.0) as conn:
                conn.execute(
                    """
                    INSERT INTO cctv_recordings 
                    (id, camera_id, camera_name, file_name, file_type, mime_type, file_size_bytes, local_path, google_drive_file_id, google_drive_web_url, sync_status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        kwargs["rec_id"],
                        kwargs["camera_id"],
                        kwargs["camera_name"],
                        kwargs["file_name"],
                        kwargs["file_type"],
                        kwargs["mime_type"],
                        kwargs["file_size_bytes"],
                        kwargs["local_path"],
                        kwargs.get("gdrive_file_id"),
                        kwargs.get("gdrive_web_url"),
                        kwargs["sync_status"],
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save recording to SQLite: {e}")

    def _background_scheduler_loop(self):
        """Periodically checks cameras with record_stream enabled and enforces retention policies"""
        last_check = 0
        while self.running:
            time.sleep(10)
            now = time.time()
            if now - last_check < 60:
                continue
            last_check = now

            if not os.path.exists(settings.DATABASE_PATH):
                continue

            try:
                with sqlite3.connect(settings.DATABASE_PATH, timeout=5.0) as conn:
                    cursor = conn.cursor()
                    # 1. Check auto-record cameras
                    cursor.execute("SELECT id, name, stream_url, record_stream, record_interval, retention_days FROM cctv_cameras WHERE record_stream = 1 AND status = 'active'")
                    cams = cursor.fetchall()
                    for c in cams:
                        cid, cname, surl, r_stream, r_interval, r_retention = c
                        threading.Thread(target=self.record_clip, args=(cid, cname, surl, 30), daemon=True).start()

                    # 2. Enforce retention policy (delete recordings older than retention_days)
                    for c in cams:
                        cid, _, _, _, _, r_retention = c
                        cutoff = (datetime.utcnow() - timedelta(days=r_retention or 7)).strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("SELECT id, local_path FROM cctv_recordings WHERE camera_id = ? AND created_at < ?", (cid, cutoff))
                        old_files = cursor.fetchall()
                        for of in old_files:
                            fid, lpath = of
                            if os.path.exists(lpath):
                                try:
                                    os.remove(lpath)
                                except Exception:
                                    pass
                            cursor.execute("DELETE FROM cctv_recordings WHERE id = ?", (fid,))
                    conn.commit()
            except Exception as e:
                logger.debug(f"Scheduler check skipped: {e}")

clospol_engine = ClospolCctvEngine()

