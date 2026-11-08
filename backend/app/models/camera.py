from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from app.core.database import Base

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, default="General Area")
    stream_url = Column(String, nullable=False)
    protocol = Column(String, default="RTSP")
    ip_address = Column(String, nullable=True)
    onvif_port = Column(Integer, default=80)

    is_active = Column(Boolean, default=True)
    status = Column(String, default="ONLINE")
    fps = Column(Integer, default=25)

    enable_counting = Column(Boolean, default=True)
    enable_suspicious = Column(Boolean, default=True)
    enable_face_rec = Column(Boolean, default=True)

    roi_zones = Column(JSON, default=list)
    counting_lines = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
