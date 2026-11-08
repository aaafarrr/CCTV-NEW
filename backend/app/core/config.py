import os
import secrets
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CCTV NEW - Enterprise AI Surveillance & Multi-Cloud NVR"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cctv_new_enterprise_hmac_secret_2026_9f8a7b6c5d4e3f2a1b")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./cctv_enterprise.db"
    )

    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION: str = "face_embeddings"

    MEDIA_DIR: str = os.getenv("MEDIA_DIR", "./media")
    CROP_DIR: str = os.getenv("CROP_DIR", "./media/crops")
    FACES_DIR: str = os.getenv("FACES_DIR", "./media/faces")
    CLIPS_DIR: str = os.getenv("CLIPS_DIR", "./media/clips")

    AI_DEVICE: str = os.getenv("AI_DEVICE", "auto")
    FRAME_SKIP: int = int(os.getenv("FRAME_SKIP", "2"))
    MOTION_PREFILTER_ENABLED: bool = True

    TIMEZONE_OFFSET_HOURS: int = int(os.getenv("TIMEZONE_OFFSET_HOURS", "7"))
    TIMEZONE_NAME: str = os.getenv("TIMEZONE_NAME", "WIB (UTC+7)")

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    class Config:
        case_sensitive = True

settings = Settings()

for path in [settings.MEDIA_DIR, settings.CROP_DIR, settings.FACES_DIR, settings.CLIPS_DIR]:
    os.makedirs(path, exist_ok=True)

