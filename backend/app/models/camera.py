from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON
from app.core.database import Base

class Camera(Base):
    """
    CCTV Camera entity matching Clospol schema.prisma (CctvCamera)
    """
    __tablename__ = "cctv_cameras"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    stream_url = Column(String, nullable=False)
    snapshot_url = Column(String, nullable=True)
    schedule_cron = Column(String, nullable=True)
    record_stream = Column(Boolean, default=False)
    record_interval = Column(Integer, default=5) # minutes
    retention_days = Column(Integer, default=7)
    status = Column(String, default="active") # active, inactive, error

    snapshot_headers = Column(JSON, default=dict)
    last_capture_at = Column(DateTime, nullable=True)
    last_capture_status = Column(String, nullable=True)
    last_capture_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CctvRecording(Base):
    """
    CCTV Recording file log (matching Clospol files mapped to folders)
    """
    __tablename__ = "cctv_recordings"

    id = Column(String, primary_key=True, index=True)
    camera_id = Column(String, index=True, nullable=False)
    camera_name = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, default="video") # video or image
    mime_type = Column(String, default="video/mp4")
    file_size_bytes = Column(Integer, default=0)
    local_path = Column(String, nullable=False)

    # Google Drive Sync Info
    google_drive_file_id = Column(String, nullable=True, index=True)
    google_drive_web_url = Column(String, nullable=True)
    sync_status = Column(String, default="local") # local, synced, failed

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
