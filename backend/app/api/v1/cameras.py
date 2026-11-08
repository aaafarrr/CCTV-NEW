import os
import time
import asyncio
import cv2
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel, Field
from app.services.camera_stream import stream_manager
from app.services.v380_scanner import v380_scanner
from app.core.security import validate_safe_id, validate_safe_filename, validate_stream_url

router = APIRouter(prefix="/cameras", tags=["Cameras & PTZ"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "storage", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

class CameraConfigUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    location: str = Field(default="Area Umum", max_length=120)
    stream_url: str = Field(default="synthetic_lobby", max_length=500)
    enable_counting: bool = True
    enable_suspicious: bool = True
    enable_face_rec: bool = True
    roi_zones: List[Dict[str, Any]] = []
    counting_lines: List[Dict[str, Any]] = []

class PTZCommand(BaseModel):
    action: str = Field(..., description="zoom_in, zoom_out, pan_left, pan_right, tilt_up, tilt_down, reset")
    step: float = Field(default=0.15, ge=0.05, le=0.5)

@router.get("", response_model=List[Dict[str, Any]])
async def list_cameras():
    cams = []
    for cam_id, data in stream_manager.active_streams.items():
        cam_info = data["info"].copy()
        cam_info["status"] = "OFFLINE" if data.get("is_connecting") else "ONLINE"
        cam_info["ptz"] = stream_manager.ptz_states.get(cam_id, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0})
        meta = data.get("latest_metadata", {})
        cam_info["live_people"] = meta.get("people_count", 0)
        cam_info["live_vehicles"] = meta.get("vehicle_count", 0)
        cam_info["motion_energy"] = meta.get("motion_energy", 0.0)
        cams.append(cam_info)
    return cams

@router.get("/discover/onvif")
async def discover_onvif_cameras():
    return [
        {
            "ip": "192.168.1.105",
            "port": 554,
            "device_id": "ONVIF-HIK-4K01",
            "hw_model": "DS-2CD2143G2-I",
            "manufacturer": "Hikvision Enterprise",
            "rtsp_url": "synthetic_lobby",
            "sd_patch_status": "Native ONVIF Profile S/T",
            "source": "WS-Discovery Multicast 3702"
        },
        {
            "ip": "192.168.1.109",
            "port": 554,
            "device_id": "ONVIF-DAH-PTZ2",
            "hw_model": "IPC-HFW2431S",
            "manufacturer": "Dahua Technology",
            "rtsp_url": "synthetic_parking",
            "sd_patch_status": "Native ONVIF Profile S",
            "source": "WS-Discovery Multicast 3702"
        }
    ]

@router.get("/discover/v380")
async def discover_v380_cameras():
    devices = v380_scanner.scan_lan(timeout=0.8, include_demo=True)
    guide = v380_scanner.get_rtsp_unlock_guide()
    return {
        "devices": devices,
        "unlock_guide": guide
    }

@router.get("/snapshots/download/{filename}")
async def download_snapshot(filename: str):
    safe_name = validate_safe_filename(filename)
    file_path = os.path.realpath(os.path.join(SNAPSHOT_DIR, safe_name))
    snap_root = os.path.realpath(SNAPSHOT_DIR)
    if not file_path.startswith(snap_root) or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File snapshot tidak ditemukan")
    return FileResponse(file_path, media_type="image/jpeg", filename=safe_name)

@router.get("/{camera_id}", response_model=Dict[str, Any])
async def get_camera(camera_id: str):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    data = stream_manager.active_streams[cid]
    cam_info = data["info"].copy()
    cam_info["status"] = "OFFLINE" if data.get("is_connecting") else "ONLINE"
    cam_info["ptz"] = stream_manager.ptz_states.get(cid, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0})
    return cam_info

@router.put("/{camera_id}")
async def update_camera(camera_id: str, config: CameraConfigUpdate):
    cid = validate_safe_id(camera_id, "Camera ID")
    safe_url = validate_stream_url(config.stream_url)
    if cid not in stream_manager.active_streams:
        cam_info = {
            "id": cid,
            "name": config.name,
            "location": config.location,
            "stream_url": safe_url,
            "enable_counting": config.enable_counting,
            "enable_suspicious": config.enable_suspicious,
            "enable_face_rec": config.enable_face_rec,
            "roi_zones": config.roi_zones,
            "counting_lines": config.counting_lines
        }
        stream_manager.add_or_update_camera(cam_info)
    else:
        stream_manager.update_camera_config(
            camera_id=cid,
            name=config.name,
            location=config.location,
            stream_url=safe_url,
            enable_counting=config.enable_counting,
            enable_suspicious=config.enable_suspicious,
            enable_face_rec=config.enable_face_rec,
            roi_zones=config.roi_zones,
            counting_lines=config.counting_lines
        )
    return {"status": "success", "message": f"Konfigurasi kamera {cid} berhasil disimpan"}

@router.delete("/{camera_id}")
async def delete_camera(camera_id: str):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    stream_data = stream_manager.active_streams.pop(cid, None)
    if stream_data:
        stream_data["stopped"] = True
        if stream_data.get("cap"):
            try:
                stream_data["cap"].release()
            except Exception:
                pass
    stream_manager._save_persistent_cameras()
    return {"status": "success", "message": f"Kamera {cid} dihapus"}

@router.post("/{camera_id}/ptz")
async def control_camera_ptz(camera_id: str, cmd: PTZCommand):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    state = stream_manager.control_ptz(cid, cmd.action, cmd.step)
    return {"status": "success", "camera_id": cid, "ptz": state}

@router.get("/{camera_id}/timeline")
async def get_camera_timeline(camera_id: str):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    bands = stream_manager.timeline_bands.get(cid, [])
    return {
        "camera_id": cid,
        "camera_name": stream_manager.active_streams[cid]["info"].get("name", cid),
        "pre_event_buffer_frames": len(stream_manager.pre_event_buffers.get(cid, [])),
        "bands": bands
    }

@router.get("/{camera_id}/stream")
async def video_feed(
    camera_id: str,
    request: Request,
    show_boxes: bool = Query(True, description="Tampilkan overlay AI bounding box")
):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Stream kamera tidak ditemukan")

    async def frame_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                frame_bytes = stream_manager.get_latest_frame_jpeg(cid, show_boxes=show_boxes)
                if frame_bytes:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                    )
                await asyncio.sleep(0.06)
        except (asyncio.CancelledError, Exception):
            pass

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close"
        }
    )

@router.websocket("/{camera_id}/ws")
async def websocket_camera_stream(
    websocket: WebSocket,
    camera_id: str,
    show_boxes: bool = Query(True)
):
    await websocket.accept()
    last_sent_bytes = None
    try:
        while True:
            jpeg_bytes = stream_manager.get_latest_frame_jpeg(camera_id, show_boxes=show_boxes)
            if jpeg_bytes and jpeg_bytes != last_sent_bytes:
                await websocket.send_bytes(jpeg_bytes)
                last_sent_bytes = jpeg_bytes
            await asyncio.sleep(0.06)
    except (WebSocketDisconnect, asyncio.CancelledError, Exception):
        pass

@router.get("/{camera_id}/thumbnail")
async def get_camera_thumbnail(
    camera_id: str,
    show_boxes: bool = Query(True)
):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    frame_bytes = stream_manager.get_latest_frame_jpeg(cid, show_boxes=show_boxes)
    if not frame_bytes:
        raise HTTPException(status_code=404, detail="Thumbnail belum tersedia")

    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, max-age=0"}
    )

@router.post("/{camera_id}/snapshot")
async def take_camera_snapshot(camera_id: str):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    stream_data = stream_manager.active_streams[cid]
    latest_frame = stream_data.get("latest_frame")
    if latest_frame is None:
        raise HTTPException(status_code=500, detail="Frame kamera belum siap")

    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{cid}_{timestamp_str}.jpg"
    file_path = os.path.join(SNAPSHOT_DIR, filename)

    success = cv2.imwrite(file_path, latest_frame)
    if not success:
        raise HTTPException(status_code=500, detail="Gagal menyimpan file snapshot")

    download_url = f"/api/v1/cameras/snapshots/download/{filename}"
    return {
        "status": "success",
        "camera_id": cid,
        "camera_name": stream_data["info"].get("name", cid),
        "filename": filename,
        "download_url": download_url,
        "timestamp": time.time()
    }

@router.get("/{camera_id}/snapshots")
async def list_camera_snapshots(camera_id: str):
    cid = validate_safe_id(camera_id, "Camera ID")
    if not os.path.exists(SNAPSHOT_DIR):
        return []

    cam_snapshots = []
    for f in os.listdir(SNAPSHOT_DIR):
        if f.startswith(cid) and f.endswith(".jpg"):
            full_p = os.path.join(SNAPSHOT_DIR, f)
            stat = os.stat(full_p)
            cam_snapshots.append({
                "filename": f,
                "camera_id": cid,
                "download_url": f"/api/v1/cameras/snapshots/download/{f}",
                "timestamp": stat.st_mtime,
                "size_bytes": stat.st_size
            })
    cam_snapshots.sort(key=lambda x: x["timestamp"], reverse=True)
    return cam_snapshots
