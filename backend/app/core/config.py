import os
import secrets
from typing import List
from pydantic_settings import BaseSettings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _env_path(name: str, default: str) -> str:
    return os.path.abspath(os.getenv(name, default))


def _load_or_create_secret(storage_dir: str) -> str:
    """Use SECRET_KEY from env; otherwise generate once and persist so tokens survive restarts."""
    env_secret = os.getenv("SECRET_KEY", "").strip()
    if env_secret:
        if len(env_secret) < 32:
            raise RuntimeError("SECRET_KEY minimal 32 karakter")
        return env_secret
    os.makedirs(storage_dir, exist_ok=True)
    path = os.path.join(storage_dir, ".secret_key")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    key = secrets.token_urlsafe(48)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key)
    return key


STORAGE_DIR = _env_path("STORAGE_DIR", os.path.join(BACKEND_DIR, "storage"))
MEDIA_DIR = _env_path("MEDIA_DIR", os.path.join(BACKEND_DIR, "media"))


class Settings(BaseSettings):
    PROJECT_NAME: str = "CCTV NEW - Enterprise AI Surveillance NVR"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = _load_or_create_secret(STORAGE_DIR)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 12)))

    STORAGE_DIR: str = STORAGE_DIR
    MEDIA_DIR: str = MEDIA_DIR
    SNAPSHOT_DIR: str = os.path.join(MEDIA_DIR, "snapshots")
    CLIPS_DIR: str = os.path.join(MEDIA_DIR, "clips")
    FACES_DIR: str = os.path.join(MEDIA_DIR, "faces")
    CROP_DIR: str = os.path.join(MEDIA_DIR, "crops")

    # shortcut: background workers write via sqlite3 directly, so only SQLite is supported; move to a queue + async session for Postgres
    DATABASE_PATH: str = _env_path("DATABASE_PATH", os.path.join(STORAGE_DIR, "cctv.db"))

    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "face_embeddings")

    AI_DEVICE: str = os.getenv("AI_DEVICE", "cpu")  # "cpu" or CUDA index e.g. "0"
    YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    YOLO_CONFIDENCE: float = float(os.getenv("YOLO_CONFIDENCE", "0.4"))
    FACE_MODEL: str = os.getenv("FACE_MODEL", "buffalo_s")
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.45"))
    DETECT_EVERY_N_FRAMES: int = int(os.getenv("DETECT_EVERY_N_FRAMES", "3"))
    MAX_FRAME_WIDTH: int = int(os.getenv("MAX_FRAME_WIDTH", "1280"))

    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
    S3_REGION: str = os.getenv("S3_REGION", "auto")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_PREFIX: str = os.getenv("S3_PREFIX", "cctv")

    TIMEZONE_OFFSET_HOURS: int = int(os.getenv("TIMEZONE_OFFSET_HOURS", "7"))
    TIMEZONE_NAME: str = os.getenv("TIMEZONE_NAME", "WIB (UTC+7)")

    CORS_ORIGINS: List[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    FRONTEND_DIST: str = _env_path("FRONTEND_DIST", os.path.join(BACKEND_DIR, "..", "frontend", "dist"))

    class Config:
        case_sensitive = True


settings = Settings()

for path in [settings.STORAGE_DIR, settings.SNAPSHOT_DIR, settings.CLIPS_DIR, settings.FACES_DIR, settings.CROP_DIR]:
    os.makedirs(path, exist_ok=True)
