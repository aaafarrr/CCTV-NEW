import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app.core.database import get_db
from app.models.camera import Camera, CctvRecording
from app.services.cctv_engine import clospol_engine
from app.services.onvif_service import clospol_onvif
from app.core.security import get_current_user

router = APIRouter(prefix="/cctv", tags=["Clospol CCTV"])

class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    stream_url: str = Field(..., min_length=3)
    snapshot_url: Optional[str] = None
    schedule_cron: Optional[str] = None
    record_stream: bool = False
    record_interval: int = 5
    retention_days: int = 7
    snapshot_headers: Dict[str, Any] = {}

class TestConnectionRequest(BaseModel):
    stream_url: str
    snapshot_url: Optional[str] = None
    onvif_url: Optional[str] = None
    onvif_username: Optional[str] = None
    onvif_password: Optional[str] = None

@router.get("", response_model=Dict[str, Any])
async def list_cameras(_: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).order_by(Camera.created_at.desc()))
    cams = result.scalars().all()
    return {
        "cameras": [
            {
                "id": c.id,
                "name": c.name,
                "streamUrl": c.stream_url,
                "snapshotUrl": c.snapshot_url,
                "scheduleCron": c.schedule_cron,
                "recordStream": c.record_stream,
                "recordInterval": c.record_interval,
                "retentionDays": c.retention_days,
                "status": c.status,
                "snapshotHeaders": c.snapshot_headers or {},
                "lastCaptureAt": c.last_capture_at.isoformat() if c.last_capture_at else None,
                "lastCaptureStatus": c.last_capture_status,
                "lastCaptureError": c.last_capture_error,
            }
            for c in cams
        ]
    }

@router.post("", response_model=Dict[str, Any])
async def create_camera(payload: CameraCreate, _: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cam_id = f"cam_{uuid.uuid4().hex[:8]}"
    camera = Camera(
        id=cam_id,
        name=payload.name,
        stream_url=payload.stream_url,
        snapshot_url=payload.snapshot_url,
        schedule_cron=payload.schedule_cron,
        record_stream=payload.record_stream,
        record_interval=payload.record_interval,
        retention_days=payload.retention_days,
        snapshot_headers=payload.snapshot_headers,
        status="active"
    )
    db.add(camera)
    await db.commit()
    return {"status": "success", "camera_id": cam_id, "message": "Kamera berhasil ditambahkan"}

@router.put("/{camera_id}", response_model=Dict[str, Any])
async def update_camera(camera_id: str, payload: CameraCreate, _: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalars().first()
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    camera.name = payload.name
    camera.stream_url = payload.stream_url
    camera.snapshot_url = payload.snapshot_url
    camera.schedule_cron = payload.schedule_cron
    camera.record_stream = payload.record_stream
    camera.record_interval = payload.record_interval
    camera.retention_days = payload.retention_days
    camera.snapshot_headers = payload.snapshot_headers

    await db.commit()
    return {"status": "success", "message": "Konfigurasi kamera berhasil diperbarui"}

@router.delete("/{camera_id}")
async def delete_camera(camera_id: str, _: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalars().first()
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    await db.delete(camera)
    await db.commit()
    return {"status": "success", "message": "Kamera berhasil dihapus"}

@router.post("/test-connection")
async def test_camera_connection(payload: TestConnectionRequest, _: Dict[str, Any] = Depends(get_current_user)):
    """Matches Clospol CctvService.testConnection"""
    try:
        onvif_details = None
        if payload.onvif_url:
            onvif_details = clospol_onvif.test_and_fetch_endpoints(
                url=payload.onvif_url,
                username=payload.onvif_username,
                password=payload.onvif_password
            )

        stream_to_test = onvif_details["rtsp_url"] if onvif_details else payload.stream_url
        is_ok = clospol_engine.test_connection(stream_to_test, payload.snapshot_url)
        return {
            "success": is_ok,
            "stream_url": stream_to_test,
            "onvif_details": onvif_details
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{camera_id}/stream")
async def get_live_mjpeg_stream(camera_id: str, request: Request, _: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Real-time live video feed rendered directly in browser"""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalars().first()
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    async def stream_generator():
        import asyncio
        while True:
            if await request.is_disconnected():
                break
            frame = clospol_engine.get_latest_jpeg(camera.id, camera.stream_url)
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            await asyncio.sleep(0.05)

    return StreamingResponse(
        stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@router.post("/{camera_id}/capture")
async def capture_snapshot_now(camera_id: str, _: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Takes a manual snapshot and syncs to Google Drive"""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalars().first()
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    try:
        data = clospol_engine.capture_snapshot(camera.id, camera.name, camera.stream_url)
        return {"status": "success", "snapshot": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{camera_id}/record-clip")
async def record_clip_now(camera_id: str, duration: int = Query(15), _: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Records a clip and uploads to Google Drive"""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalars().first()
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    try:
        clip_data = clospol_engine.record_clip(camera.id, camera.name, camera.stream_url, duration_seconds=duration)
        return {"status": "success", "clip": clip_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{camera_id}/gallery")
async def get_camera_gallery(camera_id: str, _: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Matching Clospol /api/cctv/[id]/gallery"""
    result = await db.execute(select(CctvRecording).where(CctvRecording.camera_id == camera_id).order_by(CctvRecording.created_at.desc()))
    records = result.scalars().all()
    return {
        "files": [
            {
                "id": r.id,
                "name": r.file_name,
                "mimeType": r.mime_type,
                "fileType": r.file_type,
                "sizeBytes": r.file_size_bytes,
                "createdAt": r.created_at.isoformat(),
                "downloadUrl": f"/media/{'recordings' if r.file_type == 'video' else 'snapshots'}/{r.file_name}",
                "googleDriveUrl": r.google_drive_web_url,
                "syncStatus": r.sync_status
            }
            for r in records
        ]
    }

