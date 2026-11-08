import os
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.event import SecurityEvent
from app.services.camera_stream import stream_manager

router = APIRouter(prefix="/alerts", tags=["Alerts & Incidents"])

@router.get("", response_model=List[Dict[str, Any]])
async def get_recent_alerts(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    _: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SecurityEvent).order_by(SecurityEvent.timestamp.desc()).limit(limit)
    if severity and severity != "ALL":
        stmt = stmt.where(SecurityEvent.severity == severity.upper())
    if camera_id and camera_id != "ALL":
        stmt = stmt.where(SecurityEvent.camera_id == camera_id)

    result = await db.execute(stmt)
    events = result.scalars().all()

    alerts = []
    for evt in events:
        alerts.append({
            "id": evt.id,
            "event_type": evt.event_type,
            "severity": evt.severity,
            "camera_id": evt.camera_id,
            "camera_name": evt.camera_name,
            "description": evt.description,
            "ai_summary": evt.ai_summary or f"[AI Ringkasan] Insiden {evt.event_type} pada {evt.camera_name}.",
            "snapshot_url": evt.snapshot_url or f"/api/v1/cameras/{evt.camera_id}/thumbnail?show_boxes=true",
            "cloud_synced": bool(evt.cloud_synced),
            "timestamp": evt.timestamp.timestamp() if evt.timestamp else time.time(),
            "metadata": evt.metadata_json or {}
        })

    return alerts

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    _: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == alert_id))
    evt = result.scalars().first()
    if not evt:
        raise HTTPException(status_code=404, detail="Insiden tidak ditemukan")

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
