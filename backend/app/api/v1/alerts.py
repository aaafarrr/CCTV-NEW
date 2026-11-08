import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user, require_admin
from app.models.event import SecurityEvent
from app.services.camera_stream import stream_manager, STORAGE_DIR
from app.services.storage_gateway import storage_gateway
import os
import cv2

router = APIRouter(prefix="/alerts", tags=["Alerts & Incidents"])

class SimulateAlertRequest(BaseModel):
    event_type: str = "FALL_DETECTED"
    camera_id: str = "cam_1"

async def seed_initial_events():
    """Seed realistic enterprise security events with AI Narrative Summary if DB is empty"""
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(SecurityEvent).limit(1))).scalars().first()
        if existing:
            return

        now = datetime.utcnow()
        samples = [
            SecurityEvent(
                id="evt_seed_01",
                camera_id="cam_4",
                camera_name="Kamera Gudang & Brankas",
                event_type="INTRUSION",
                severity="CRITICAL",
                description="Pelanggaran Zona Terlarang (Zona Brankas Utama): Objek #104 (person) memasuki perimeter merah.",
                ai_summary="[AI Ringkasan] Seseorang berpakaian gelap terdeteksi memasuki Zona Brankas Utama di Lantai B1 di luar jadwal operasional. Rekaman pre-alarm 5 detik telah diamankan ke Google Drive Archive.",
                snapshot_url="/api/v1/cameras/cam_4/thumbnail?show_boxes=true",
                cloud_synced=1,
                metadata_json={"zone_name": "Zona Brankas Utama", "track_id": 104, "class_name": "person"},
                timestamp=now - timedelta(minutes=8)
            ),
            SecurityEvent(
                id="evt_seed_02",
                camera_id="cam_1",
                camera_name="Kamera Utama (Lobby)",
                event_type="FALL_DETECTED",
                severity="CRITICAL",
                description="Darurat Medis / Keamanan (Fall Detection): Subjek #109 terdeteksi terjatuh di lantai Lobby Utama!",
                ai_summary="[AI Ringkasan • DeepCamera Skill] Subjek #109 mengalami perubahan rasio postur vertikal ke horizontal secara mendadak (1.64 -> 0.58) di Kamera Utama (Lobby). Disarankan pengiriman tim medis/keamanan segera.",
                snapshot_url="/api/v1/cameras/cam_1/thumbnail?show_boxes=true",
                cloud_synced=1,
                metadata_json={"track_id": 109, "prev_aspect": 1.64, "curr_aspect": 0.58},
                timestamp=now - timedelta(minutes=19)
            ),
            SecurityEvent(
                id="evt_seed_03",
                camera_id="cam_1",
                camera_name="Kamera Utama (Lobby)",
                event_type="FACE_MATCH",
                severity="CRITICAL",
                description="Peringatan Watchlist DPO: Target Watchlist #A09 teridentifikasi (Similarity 94.6%).",
                ai_summary="[AI Ringkasan] Mesin vektor InsightFace/Qdrant mencocokkan wajah subjek di Pintu Masuk Utama dengan profil 'Target Watchlist #A09' (skor kosinus 0.946). Notifikasi dikirim ke pos komando.",
                snapshot_url="/media/faces/person_dpo_01.jpg",
                cloud_synced=1,
                metadata_json={"person_id": "person_dpo_01", "similarity": 0.946},
                timestamp=now - timedelta(minutes=28)
            ),
            SecurityEvent(
                id="evt_seed_04",
                camera_id="cam_2",
                camera_name="Kamera Area Parkir",
                event_type="LOITERING",
                severity="WARNING",
                description="Aktivitas Mencurigakan (Loitering): Target #112 berdiam di Jalur Evakuasi Darurat selama 14 detik.",
                ai_summary="[AI Ringkasan] Subjek pejalan kaki #112 terpantau berhenti di Jalur Evakuasi Darurat Gedung B melebihi batas waktu aman (14s > 6s).",
                snapshot_url="/api/v1/cameras/cam_2/thumbnail?show_boxes=true",
                cloud_synced=1,
                metadata_json={"zone_name": "Jalur Evakuasi Darurat", "dwell_seconds": 14},
                timestamp=now - timedelta(minutes=45)
            ),
        ]
        for s in samples:
            db.add(s)
        await db.commit()

@router.get("", response_model=List[Dict[str, Any]])
async def get_recent_alerts(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SecurityEvent).order_by(SecurityEvent.timestamp.desc()).limit(limit)
    if severity and severity != "ALL":
        stmt = stmt.where(SecurityEvent.severity == severity.upper())
    if camera_id and camera_id != "ALL":
        stmt = stmt.where(SecurityEvent.camera_id == camera_id)

    result = await db.execute(stmt)
    events = result.scalars().all()

    seen_ids = set()
    alerts = []
    for evt in events:
        seen_ids.add(evt.id)
        alerts.append({
            "id": evt.id,
            "event_type": evt.event_type,
            "severity": evt.severity,
            "camera_id": evt.camera_id,
            "camera_name": evt.camera_name,
            "description": evt.description,
            "ai_summary": evt.ai_summary or f"[AI Ringkasan] Insiden {evt.event_type} tercatat pada {evt.camera_name}.",
            "snapshot_url": evt.snapshot_url or f"/api/v1/cameras/{evt.camera_id}/thumbnail?show_boxes=true",
            "cloud_synced": bool(evt.cloud_synced),
            "timestamp": evt.timestamp.timestamp() if evt.timestamp else time.time(),
            "metadata": evt.metadata_json or {}
        })

    for rt in list(stream_manager.recent_runtime_alerts)[:10]:
        rt_id = rt.get("id", f"rt_{uuid.uuid4().hex[:6]}")
        if rt_id in seen_ids:
            continue
        if severity and severity != "ALL" and rt.get("severity") != severity.upper():
            continue
        if camera_id and camera_id != "ALL" and rt.get("camera_id") != camera_id:
            continue
        alerts.insert(0, {
            "id": rt_id,
            "event_type": rt.get("event_type", "INTRUSION"),
            "severity": rt.get("severity", "CRITICAL"),
            "camera_id": rt.get("camera_id", "cam_1"),
            "camera_name": rt.get("camera_name", "Kamera Utama"),
            "description": rt.get("description", ""),
            "ai_summary": rt.get("ai_summary", "[AI Ringkasan] Deteksi anomali real-time oleh mesin pengawas."),
            "snapshot_url": f"/api/v1/cameras/{rt.get('camera_id', 'cam_1')}/thumbnail?show_boxes=true",
            "cloud_synced": True,
            "timestamp": rt.get("timestamp", time.time()),
            "metadata": rt.get("metadata", {})
        })

    alerts.sort(key=lambda x: x["timestamp"], reverse=True)
    return alerts[:limit]

@router.post("/simulate")
async def simulate_security_incident(
    payload: SimulateAlertRequest,
    _: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger a persisted Fall Detection or Intrusion incident for testing emergency workflows"""
    cam_data = stream_manager.active_streams.get(payload.camera_id)
    cam_name = cam_data["info"]["name"] if cam_data else "Kamera Utama (Lobby)"
    evt_id = f"evt_sim_{uuid.uuid4().hex[:8]}"
    now_str = time.strftime("%H:%M:%S")

    if payload.event_type == "FALL_DETECTED":
        desc = f"Darurat Medis / Keamanan (Fall Detection): Subjek #115 terdeteksi terjatuh di area {cam_name}!"
        summary = f"[AI Ringkasan • DeepCamera Skill] Subjek #115 mengalami perubahan postur mendadak (rasio 1.58 -> 0.54) di {cam_name} pukul {now_str}. Rekaman pre-alarm 5s telah diamankan ke Cloud Pool."
        sev = "CRITICAL"
    else:
        desc = f"Pelanggaran Perimeter Kritis: Subjek memasuki zona terlarang pada {cam_name}!"
        summary = f"[AI Ringkasan] Pelanggaran batas ROI terdeteksi pada {cam_name} pukul {now_str}. Sirine ruang kontrol diaktifkan."
        sev = "CRITICAL"

    evt = SecurityEvent(
        id=evt_id,
        camera_id=payload.camera_id,
        camera_name=cam_name,
        event_type=payload.event_type,
        severity=sev,
        description=desc,
        ai_summary=summary,
        snapshot_url=f"/api/v1/cameras/{payload.camera_id}/thumbnail?show_boxes=true",
        cloud_synced=1,
        metadata_json={"simulated": True, "camera_id": payload.camera_id},
        timestamp=datetime.utcnow()
    )
    if cam_data and cam_data.get("latest_frame") is not None:
        snap_dir = os.path.join(STORAGE_DIR, "snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        snap_file = f"{evt_id}.jpg"
        if cv2.imwrite(os.path.join(snap_dir, snap_file), cam_data["latest_frame"]):
            evt.snapshot_url = f"/api/v1/cameras/snapshots/download/{snap_file}"

    sync_job = storage_gateway.trigger_cloud_sync(
        camera_name=cam_name,
        reason=f"Auto-Sync [{sev}] {payload.event_type} ({evt_id})"
    )
    stream_manager.timeline_bands.setdefault(payload.camera_id, []).append({
        "id": evt_id,
        "hour_offset": -0.05,
        "duration_min": 8,
        "type": "INTRUSION",
        "color": "#ef4444",
        "label": desc[:48],
        "timestamp": time.time()
    })
    db.add(evt)
    await db.commit()
    return {
        "status": "success",
        "id": evt_id,
        "event_type": payload.event_type,
        "severity": sev,
        "camera_name": cam_name,
        "description": desc,
        "ai_summary": summary,
        "snapshot_url": evt.snapshot_url,
        "cloud_sync_job": sync_job
    }

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    _: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stream_manager.recent_runtime_alerts = type(stream_manager.recent_runtime_alerts)(
        [a for a in stream_manager.recent_runtime_alerts if a.get("id") != alert_id],
        maxlen=40
    )
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == alert_id))
    evt = result.scalars().first()
    if evt:
        await db.delete(evt)
        await db.commit()
    return {"status": "success", "message": f"Insiden {alert_id} berhasil dihapus"}

@router.delete("")
async def clear_all_alerts(
    _: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stream_manager.recent_runtime_alerts.clear()
    await db.execute(delete(SecurityEvent))
    await db.commit()
    return {"status": "success", "message": "Seluruh log insiden berhasil dibersihkan"}
