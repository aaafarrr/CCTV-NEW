import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import auth, cctv, google_drive_api
from app.services.cctv_engine import clospol_engine

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.5.0",
    description="Clospol CCTV Surveillance & Google Drive Multi-Tier Storage Gateway"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.MEDIA_DIR, exist_ok=True)
os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)
os.makedirs(settings.SNAPSHOTS_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(cctv.router, prefix=settings.API_V1_STR)
app.include_router(google_drive_api.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    clospol_engine.stop()

@app.get("/")
async def root():
    return {
        "status": "ONLINE",
        "system": settings.PROJECT_NAME,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
