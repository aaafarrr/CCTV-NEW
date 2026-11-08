import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import cameras, analytics, alerts, faces, search, auth, storage
from app.services.camera_stream import stream_manager
from app.services.face_search_service import face_search_service

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Enterprise CCTV NVR with AI Object Detection, Google-Photos Face Vector Search, V380 Discovery & Multi-Cloud Storage Pool"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(cameras.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(faces.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(storage.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    await init_db()
    await auth.seed_initial_users()
    await face_search_service.seed_initial_identities()
    await alerts.seed_initial_events()

@app.on_event("shutdown")
async def shutdown_event():
    stream_manager.stop_all()

@app.get("/")
async def root():
    return {
        "status": "ONLINE",
        "system": settings.PROJECT_NAME,
        "docs": "/docs",
        "ai_device": settings.AI_DEVICE
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

