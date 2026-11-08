import os
import time
import asyncio
import cv2
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel, Field
from app.core.config import settings
from app.services.camera_stream import stream_manager
from app.services.v380_scanner import v380_scanner
from app.core.security import (
    validate_safe_id,
    validate_safe_filename,
    validate_stream_url,
    mask_stream_url,
    get_current_user,
    require_admin,
    require_operator
)

router = APIRouter(prefix="/cameras", tags=["Cameras & PTZ"])

class CameraConfigUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    location: str = Field(default="Area Pengawasan", max_length=120)
    stream_url: str = Field(..., min_length=5, max_length=500)
    enable_counting: bool = True
    enable_suspicious: bool = True
    enable_face_rec: bool = True
    roi_zones: List[Dict[str, Any]] = []
    counting_lines: List[Dict[str, Any]] = []

class PTZCommand(BaseModel):
    action: str = Field(..., description="zoom_in, zoom_out, pan_left, pan_right, tilt_up, tilt_down, reset")
    step: float = Field(default=0.15, ge=0.05, le=0.5)

@router.get("", response_model=List[Dict[str, Any]])
async def list_cameras(_: Dict[str, Any] = Depends(get_current_user)):
    cams = []
    for cam_id, data in stream_manager.active_streams.items():
        cam_info = data["info"].copy()
        # Mask sensitive RTSP passwords before returning to client
        cam_info["stream_url_masked"] = mask_stream_url(cam_info.get("stream_url", ""))
        cam_info["status"] = "OFFLINE" if data.get("is_connecting") else "ONLINE"
        cam_info["ptz"] = stream_manager.ptz_states.get(cam_id, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0})
        meta = data.get("latest_metadata", {})
        cam_info["live_people"] = meta.get("people_count", 0)
        cam_info["live_vehicles"] = meta.get("vehicle_count", 0)
        cam_info["motion_energy"] = meta.get("motion_energy", 0.0)
        cams.append(cam_info)
    return cams

@router.get("/discover/onvif")
async def discover_onvif_cameras(_: Dict[str, Any] = Depends(require_admin)):
    return v380_scanner.scan_onvif_lan(timeout=1.2)

@router.get("/discover/v380")
async def discover_v380_cameras(_: Dict[str, Any] = Depends(require_admin)):
    devices = v380_scanner.scan_lan(timeout=1.2)
    guide = v380_scanner.get_rtsp_unlock_guide()
    return {
        "devices": devices,
        "unlock_guide": guide
    }

@router.get("/snapshots/download/{filename}")
async def download_snapshot(filename: str, _: Dict[str, Any] = Depends(get_current_user)):
    safe_name = validate_safe_filename(filename)
    file_path = os.path.realpath(os.path.join(settings.SNAPSHOT_DIR, safe_name))
    snap_root = os.path.realpath(settings.SNAPSHOT_DIR)
    if not file_path.startswith(snap_root) or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File snapshot tidak ditemukan")
    return FileResponse(file_path, media_type="image/jpeg", filename=safe_name)

@router.get("/{camera_id}", response_model=Dict[str, Any])
async def get_camera(camera_id: str, _: Dict[str, Any] = Depends(get_current_user)):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    data = stream_manager.active_streams[cid]
    cam_info = data["info"].copy()
    cam_info["stream_url_masked"] = mask_stream_url(cam_info.get("stream_url", ""))
    cam_info["status"] = "OFFLINE" if data.get("is_connecting") else "ONLINE"
    cam_info["ptz"] = stream_manager.ptz_states.get(cid, {"pan": 0.0, "tilt": 0.0, "zoom": 1.0})
    return cam_info

@router.put("/{camera_id}")
async def update_camera(camera_id: str, config: CameraConfigUpdate, _: Dict[str, Any] = Depends(require_admin)):
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
async def delete_camera(camera_id: str, _: Dict[str, Any] = Depends(require_admin)):
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
    return {"status": "success", "message": f"Kamera {cid} berhasil dihapus"}

@router.post("/{camera_id}/ptz")
async def control_camera_ptz(camera_id: str, cmd: PTZCommand, _: Dict[str, Any] = Depends(require_operator)):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    state = stream_manager.control_ptz(cid, cmd.action, cmd.step)
    return {"status": "success", "camera_id": cid, "ptz": state}

@router.get("/{camera_id}/timeline")
async def get_camera_timeline(camera_id: str, _: Dict[str, Any] = Depends(get_current_user)):
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

@router.get("/{camera_id}/replay")
async def replay_pre_event_buffer(
    camera_id: str,
    request: Request,
    label: str = Query("INSIDEN", description="Label insiden pada overlay OSD replay"),
    _: Dict[str, Any] = Depends(get_current_user)
):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    frames = stream_manager.get_pre_event_replay_frames(cid, label=label)
    if not frames:
        raise HTTPException(status_code=404, detail="Belum ada rekaman ring-buffer pre-event untuk kamera ini")

    async def replay_generator():
        idx = 0
        try:
            while True:
                if await request.is_disconnected():
                    break
                jpg = frames[idx % len(frames)]
                idx += 1
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
                )
                await asyncio.sleep(0.08)
        except (asyncio.CancelledError, Exception):
            pass

    return StreamingResponse(
        replay_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate, max-age=0"}
    )

@router.get("/{camera_id}/stream")
async def video_feed(
    camera_id: str,
    request: Request,
    show_boxes: bool = Query(True, description="Tampilkan overlay AI bounding box"),
    _: Dict[str, Any] = Depends(get_current_user)
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
                await asyncio.sleep(0.04)
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

@router.get("/{camera_id}/thumbnail")
async def get_camera_thumbnail(
    camera_id: str,
    show_boxes: bool = Query(True),
    _: Dict[str, Any] = Depends(get_current_user)
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
async def take_camera_snapshot(camera_id: str, _: Dict[str, Any] = Depends(require_operator)):
    cid = validate_safe_id(camera_id, "Camera ID")
    if cid not in stream_manager.active_streams:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    stream_data = stream_manager.active_streams[cid]
    latest_frame = stream_data.get("latest_frame")
    if latest_frame is None:
        raise HTTPException(status_code=500, detail="Frame kamera belum siap")

    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{cid}_{timestamp_str}.jpg"
    file_path = os.path.join(settings.SNAPSHOT_DIR, filename)

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
