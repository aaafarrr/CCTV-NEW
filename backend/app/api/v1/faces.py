from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.face import PersonIdentity
from app.core.qdrant_client import vector_service
from app.core.security import validate_safe_id

router = APIRouter(prefix="/faces", tags=["Face Gallery"])

class PersonUpdate(BaseModel):
    name: str
    is_watchlist: bool = False
    notes: Optional[str] = None

@router.get("/people-clusters", response_model=List[Dict[str, Any]])
async def get_people_clusters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PersonIdentity).order_by(PersonIdentity.last_seen.desc()))
    persons = result.scalars().all()

    clusters = []
    for p in persons:
        clusters.append({
            "person_id": p.id,
            "name": p.name,
            "thumbnail_url": p.thumbnail_url or "/media/faces/default_face.png",
            "is_watchlist": p.is_watchlist,
            "appearance_count": p.appearance_count,
            "notes": p.notes or "",
            "last_seen_camera": getattr(p, "last_seen_camera", None) or "Kamera Utama (Lobby)",
            "last_seen_timestamp": p.last_seen.timestamp() if p.last_seen else 0
        })
    return clusters

@router.put("/people-clusters/{person_id}")
async def update_person_identity(person_id: str, payload: PersonUpdate, db: AsyncSession = Depends(get_db)):
    pid = validate_safe_id(person_id, "Person ID")
    result = await db.execute(select(PersonIdentity).where(PersonIdentity.id == pid))
    person = result.scalars().first()
    if not person:
        raise HTTPException(status_code=404, detail="Identitas wajah tidak ditemukan")

    person.name = payload.name
    person.is_watchlist = payload.is_watchlist
    if payload.notes is not None:
        person.notes = payload.notes

    await db.commit()
    return {"status": "success", "message": "Identitas berhasil diperbarui", "person_id": pid}

@router.delete("/people-clusters/{person_id}")
async def delete_person_identity(person_id: str, db: AsyncSession = Depends(get_db)):
    pid = validate_safe_id(person_id, "Person ID")
    result = await db.execute(select(PersonIdentity).where(PersonIdentity.id == pid))
    person = result.scalars().first()
    if not person:
        raise HTTPException(status_code=404, detail="Identitas wajah tidak ditemukan")

    await db.delete(person)
    await db.commit()
    vector_service.delete_face_embedding(pid)

    return {"status": "success", "message": f"Identitas {pid} berhasil dihapus dari SQL & Qdrant"}
