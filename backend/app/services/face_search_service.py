import os
import uuid
import time
import logging
from typing import List, Dict, Any
from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal
from app.models.face import PersonIdentity
from app.core.qdrant_client import vector_service
from app.core.config import settings
from app.services.ai.face_engine import face_engine

logger = logging.getLogger("cctv_new.face_search")

class ProductionFaceSearchService:
    """
    Real Facial Vector Indexing and Search Service.
    Persists photos cleanly to disk and vectors to Qdrant.
    Zero synthetic or dummy faces seeded.
    """
    def search_person_by_image(self, image_bytes: bytes, limit: int = 12, threshold: float = 0.4) -> List[Dict[str, Any]]:
        query_vector = face_engine.extract_vector_from_image_bytes(image_bytes)
        raw_matches = vector_service.search(
            query_vector=query_vector,
            limit=limit,
            score_threshold=threshold,
            kind=None
        )

        results = []
        for match in raw_matches:
            payload = match.get("payload", {})
            results.append({
                "face_id": payload.get("person_id") or payload.get("id"),
                "similarity_score": match.get("score"),
                "person_name": payload.get("person_name", "Subjek Tidak Dikenal"),
                "person_id": payload.get("person_id"),
                "is_watchlist": bool(payload.get("is_watchlist", False)),
                "camera_id": payload.get("camera_id", "cam_1"),
                "camera_name": payload.get("camera_name", "Kamera Utama"),
                "image_crop_url": payload.get("image_crop_url", ""),
                "timestamp": payload.get("timestamp", time.time())
            })
        return results

    async def register_new_identity_async(self, name: str, is_watchlist: bool, image_bytes: bytes, notes: str = "") -> Dict[str, Any]:
        person_id = f"person_{uuid.uuid4().hex[:8]}"
        query_vector = face_engine.extract_vector_from_image_bytes(image_bytes)

        os.makedirs(settings.FACES_DIR, exist_ok=True)
        filename = f"{person_id}.jpg"
        filepath = os.path.join(settings.FACES_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        thumb_url = f"/media/faces/{filename}"
        payload = {
            "kind": "identity",
            "person_id": person_id,
            "person_name": name,
            "is_watchlist": is_watchlist,
            "camera_id": "manual",
            "camera_name": "Registrasi Identitas Wajah",
            "image_crop_url": thumb_url,
            "timestamp": time.time()
        }

        success = vector_service.upsert(
            point_id=person_id,
            vector=query_vector,
            payload=payload
        )

        async with AsyncSessionLocal() as db:
            person = PersonIdentity(
                id=person_id,
                name=name,
                cluster_id=f"cluster_{person_id}",
                notes=notes or ("Target Watchlist" if is_watchlist else "Identitas Terdaftar"),
                thumbnail_url=thumb_url,
                last_seen_camera="Registrasi Sistem",
                is_known=True,
                is_watchlist=is_watchlist,
                appearance_count=1
            )
            db.add(person)
            await db.commit()

        return {
            "success": success,
            "person_id": person_id,
            "person_name": name,
            "thumbnail_url": thumb_url,
            "is_watchlist": is_watchlist
        }

face_search_service = ProductionFaceSearchService()
