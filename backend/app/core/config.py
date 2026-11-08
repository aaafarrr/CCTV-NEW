import os
import secrets
from typing import List
from pydantic_settings import BaseSettings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _env_path(name: str, default: str) -> str:
    return os.path.abspath(os.getenv(name, default))

STORAGE_DIR = _env_path("STORAGE_DIR", os.path.join(BACKEND_DIR, "storage"))
MEDIA_DIR = _env_path("MEDIA_DIR", os.path.join(BACKEND_DIR, "media"))

class Settings(BaseSettings):
    PROJECT_NAME: str = "Clospol CCTV - Cloud Storage & Stream Surveillance"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "clospol_cctv_secret_key_production_2026_super_safe_token")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    STORAGE_DIR: str = STORAGE_DIR
    MEDIA_DIR: str = MEDIA_DIR
    RECORDINGS_DIR: str = os.path.join(MEDIA_DIR, "recordings")
    SNAPSHOTS_DIR: str = os.path.join(MEDIA_DIR, "snapshots")

    DATABASE_PATH: str = _env_path("DATABASE_PATH", os.path.join(STORAGE_DIR, "clospol.db"))

    # Google Drive Integration (from Clospol)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REFRESH_TOKEN: str = os.getenv("GOOGLE_REFRESH_TOKEN", "")
    GOOGLE_ROOT_FOLDER: str = os.getenv("GOOGLE_ROOT_FOLDER", "CCTV Recordings")

    TIMEZONE_OFFSET_HOURS: int = int(os.getenv("TIMEZONE_OFFSET_HOURS", "7"))
    TIMEZONE_NAME: str = os.getenv("TIMEZONE_NAME", "Asia/Jakarta")

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    class Config:
        case_sensitive = True

settings = Settings()

for p in [settings.STORAGE_DIR, settings.MEDIA_DIR, settings.RECORDINGS_DIR, settings.SNAPSHOTS_DIR]:
    os.makedirs(p, exist_ok=True)
