import uuid
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.config import settings

logger = logging.getLogger("cctv_new.qdrant")

def _to_qdrant_uuid(point_id: str) -> str:
    """Convert arbitrary string ID to deterministic UUIDv5 required by Qdrant points"""
    try:
        return str(uuid.UUID(str(point_id)))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(point_id)))

class QdrantVectorService:
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_size = 512
        self.is_connected = False
        self.mode = "in-memory"
        self._init_client()

    def _init_client(self):
        try:
            self.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=1.0,
                check_compatibility=False
            )
            self._ensure_collection()
            self.is_connected = True
            self.mode = "remote"
            logger.info("Connected to Qdrant Vector DB server")
        except Exception:
            try:
                self.client = QdrantClient(":memory:")
                self._ensure_collection()
                self.is_connected = True
                self.mode = "in-memory"
                logger.info("Initialized In-Memory Qdrant Vector Store")
            except Exception as ex:
                logger.error(f"In-memory Qdrant initialization failed: {ex}")
                self.is_connected = False

    def _ensure_collection(self):
        if not self.client:
            return
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )

    def upsert_face_embedding(
        self,
        point_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> bool:
        if not self.client:
            return False
        try:
            q_id = _to_qdrant_uuid(point_id)
            full_payload = dict(payload)
            full_payload.setdefault("person_id", point_id)
            point = PointStruct(
                id=q_id,
                vector=vector,
                payload=full_payload
            )
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            return True
        except Exception as e:
            logger.error(f"Error upserting vector to Qdrant: {e}")
            return False

    def delete_face_embedding(self, point_id: str) -> bool:
        if not self.client:
            return False
        try:
            q_id = _to_qdrant_uuid(point_id)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[q_id]
            )
            return True
        except Exception:
            return False

    def search_similar_faces(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.35,
        camera_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            query_filter = None
            if camera_id:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="camera_id",
                            match=MatchValue(value=camera_id)
                        )
                    ]
                )

            try:
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=query_filter
                )
            except Exception:
                results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=query_filter
                ).points

            output = []
            for res in results:
                pl = res.payload or {}
                output.append({
                    "id": pl.get("person_id", str(res.id)),
                    "score": round(float(res.score), 4),
                    "payload": pl
                })
            return output
        except Exception as e:
            logger.error(f"Error searching faces in Qdrant: {e}")
            return []

vector_service = QdrantVectorService()

