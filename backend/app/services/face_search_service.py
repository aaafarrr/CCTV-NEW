import os
import uuid
import time
import logging
import numpy as np
import cv2
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal
from app.models.face import PersonIdentity
from app.core.qdrant_client import vector_service
from app.core.config import settings
from app.services.ai.face_engine import face_engine

logger = logging.getLogger("cctv_new.face_search")

class FaceSearchService:
    """
    Google-Photos style Facial Recognition Search & Indexing Engine.
    """
    def _create_synthetic_portrait(self, filepath: str, bg_bgr: tuple, shirt_bgr: tuple, skin_bgr: tuple, label_code: str) -> bytes:
        img = np.zeros((160, 160, 3), dtype=np.uint8)
        img[:] = bg_bgr
        # Shoulders / Suit
        cv2.ellipse(img, (80, 155), (52, 38), 0, 180, 360, shirt_bgr, -1)
        # Neck
        cv2.rectangle(img, (68, 95), (92, 122), skin_bgr, -1)
        # Head
        cv2.circle(img, (80, 68), 34, skin_bgr, -1)
        # Hair
        cv2.ellipse(img, (80, 48), (35, 22), 0, 180, 360, (35, 35, 40), -1)
        # Eyes
        cv2.circle(img, (68, 66), 4, (25, 25, 25), -1)
        cv2.circle(img, (92, 66), 4, (25, 25, 25), -1)
        # Smile
        cv2.ellipse(img, (80, 80), (12, 6), 0, 0, 180, (60, 60, 140), 2)
        # Badge tag
        cv2.rectangle(img, (0, 136), (160, 160), (15, 23, 42), -1)
        cv2.putText(img, label_code, (10, 153), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.imwrite(filepath, img)
        ret, buf = cv2.imencode(".jpg", img)
        return buf.tobytes() if ret else b""

    async def seed_initial_identities(self):
        """Ensure initial gallery identities and vector embeddings exist so Face Search works out of the box"""
        os.makedirs(settings.FACES_DIR, exist_ok=True)
        default_path = os.path.join(settings.FACES_DIR, "default_face.png")
        if not os.path.exists(default_path):
            self._create_synthetic_portrait(default_path, (235, 240, 245), (180, 90, 40), (180, 205, 230), "ID-PROFILE")

        seed_profiles = [
            {
                "id": "person_vip_01",
                "name": "Budi Santoso (Direktur Operasional)",
                "notes": "Akses VIP Seluruh Gedung & Ruang Server",
                "is_watchlist": False,
                "camera": "Kamera Utama (Lobby)",
                "count": 24,
                "bg": (240, 235, 225),
                "shirt": (160, 75, 25),
                "skin": (175, 205, 235),
                "code": "VIP • EXEC"
            },
            {
                "id": "person_dpo_01",
                "name": "Target Watchlist #A09 (Suspek Intrusi)",
                "notes": "PERINGATAN: Terdeteksi mencoba akses pintu brankas tanpa izin",
                "is_watchlist": True,
                "camera": "Kamera Gudang & Brankas",
                "count": 3,
                "bg": (210, 210, 245),
                "shirt": (45, 45, 210),
                "skin": (160, 190, 220),
                "code": "ALERT • DPO"
            },
            {
                "id": "person_staff_02",
                "name": "Siti Rahmawati (Kepala Keamanan)",
                "notes": "Petugas Patroli Shift Pagi & Sore",
                "is_watchlist": False,
                "camera": "Kamera Area Parkir",
                "count": 41,
                "bg": (225, 245, 230),
                "shirt": (95, 145, 35),
                "skin": (185, 210, 238),
                "code": "STAFF • SEC"
            },
            {
                "id": "person_kurir_03",
                "name": "Andi Pratama (Vendor Logistik)",
                "notes": "Pengiriman rutin area kargo & loading dock",
                "is_watchlist": False,
                "camera": "Kamera Gerbang Kargo",
                "count": 9,
                "bg": (220, 238, 250),
                "shirt": (30, 140, 230),
                "skin": (170, 198, 225),
                "code": "VENDOR • LOG"
            }
        ]

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PersonIdentity))
            existing = {p.id: p for p in result.scalars().all()}

            for prof in seed_profiles:
                pid = prof["id"]
                fname = f"{pid}.jpg"
                fpath = os.path.join(settings.FACES_DIR, fname)
                img_bytes = self._create_synthetic_portrait(fpath, prof["bg"], prof["shirt"], prof["skin"], prof["code"])
                vec = face_engine.extract_vector_from_image_bytes(img_bytes)

                vector_service.upsert_face_embedding(
                    point_id=pid,
                    vector=vec,
                    payload={
                        "person_id": pid,
                        "person_name": prof["name"],
                        "is_watchlist": prof["is_watchlist"],
                        "camera_id": "cam_1",
                        "camera_name": prof["camera"],
                        "image_crop_url": f"/media/faces/{fname}",
                        "timestamp": time.time() - 600
                    }
                )

                if pid not in existing:
                    db.add(PersonIdentity(
                        id=pid,
                        name=prof["name"],
                        cluster_id=f"cluster_{pid}",
                        notes=prof["notes"],
                        thumbnail_url=f"/media/faces/{fname}",
                        last_seen_camera=prof["camera"],
                        is_known=True,
                        is_watchlist=prof["is_watchlist"],
                        appearance_count=prof["count"],
                        last_seen=datetime.utcnow()
                    ))
            await db.commit()

    def search_person_by_image(self, image_bytes: bytes, limit: int = 12, threshold: float = 0.25) -> List[Dict[str, Any]]:
        query_vector = face_engine.extract_vector_from_image_bytes(image_bytes)
        raw_matches = vector_service.search_similar_faces(
            query_vector=query_vector,
            limit=limit,
            score_threshold=threshold
        )

        results = []
        for match in raw_matches:
            payload = match.get("payload", {})
            results.append({
                "face_id": match.get("id"),
                "similarity_score": match.get("score"),
                "person_name": payload.get("person_name", "Unidentified Person"),
                "person_id": payload.get("person_id"),
                "is_watchlist": bool(payload.get("is_watchlist", False)),
                "camera_id": payload.get("camera_id", "cam_1"),
                "camera_name": payload.get("camera_name", "Kamera Utama (Lobby)"),
                "image_crop_url": payload.get("image_crop_url", "/media/faces/default_face.png"),
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
            "person_id": person_id,
            "person_name": name,
            "is_watchlist": is_watchlist,
            "camera_id": "cam_1",
            "camera_name": "Registrasi Database Wajah",
            "image_crop_url": thumb_url,
            "timestamp": time.time()
        }

        success = vector_service.upsert_face_embedding(
            point_id=person_id,
            vector=query_vector,
            payload=payload
        )

        async with AsyncSessionLocal() as db:
            person = PersonIdentity(
                id=person_id,
                name=name,
                cluster_id=f"cluster_{person_id}",
                notes=notes or ("Target Watchlist Prioritas" if is_watchlist else "Identitas Terdaftar"),
                thumbnail_url=thumb_url,
                last_seen_camera="Registrasi Manual",
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

face_search_service = FaceSearchService()

