import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range, FilterSelector,
)
from app.core.config import settings

logger = logging.getLogger("cctv_new.qdrant")


def _to_qdrant_uuid(point_id: str) -> str:
    """Convert arbitrary string ID to deterministic UUIDv5 required by Qdrant points"""
    try:
        return str(uuid.UUID(str(point_id)))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(point_id)))


class QdrantVectorService:
    """512-d face vectors. Payload `kind` is "identity" (registered person) or "sighting" (seen on camera)."""

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_size = 512
        self.mode = "disconnected"
        self._init_client()

    def _init_client(self):
        if settings.QDRANT_HOST:
            try:
                self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=5.0)
                self._ensure_collection()
                self.mode = "remote"
                return
            except Exception as e:
                logger.error(f"Qdrant server {settings.QDRANT_HOST} tidak dapat dihubungi, memakai penyimpanan lokal: {e}")
        # Embedded on-disk mode keeps vectors across restarts when no Qdrant server is configured
        self.client = QdrantClient(path=os.path.join(settings.STORAGE_DIR, "qdrant"))
        self._ensure_collection()
        self.mode = "local"

    def _ensure_collection(self):
        names = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )

    def upsert(self, point_id: str, vector: List[float], payload: Dict[str, Any]) -> bool:
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(id=_to_qdrant_uuid(point_id), vector=vector, payload=payload)]
            )
            return True
        except Exception as e:
            logger.error(f"Error upserting vector to Qdrant: {e}")
            return False

    def search(self, query_vector: List[float], limit: int = 10, score_threshold: float = 0.4,
               kind: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            q_filter = Filter(must=[FieldCondition(key="kind", match=MatchValue(value=kind))]) if kind else None
            res = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=q_filter,
                limit=limit,
                score_threshold=score_threshold,
            )
            return [{"score": round(float(p.score), 4), "payload": p.payload or {}} for p in res.points]
        except Exception as e:
            logger.error(f"Error searching faces in Qdrant: {e}")
            return []

    def delete_person(self, person_id: str):
        """Remove the identity vector and every sighting linked to that person."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(filter=Filter(must=[FieldCondition(key="person_id", match=MatchValue(value=person_id))]))
            )
        except Exception as e:
            logger.error(f"Error deleting person vectors: {e}")

    def delete_sightings_before(self, unix_ts: float):
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(filter=Filter(must=[
                    FieldCondition(key="kind", match=MatchValue(value="sighting")),
                    FieldCondition(key="timestamp", range=Range(lt=unix_ts)),
                ]))
            )
        except Exception as e:
            logger.error(f"Error pruning old sightings: {e}")


vector_service = QdrantVectorService()
