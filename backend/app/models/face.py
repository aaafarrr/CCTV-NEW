from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, Float
from app.core.database import Base

class PersonIdentity(Base):
    __tablename__ = "person_identities"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, default="Unidentified Person")
    cluster_id = Column(String, index=True, nullable=True)
    notes = Column(Text, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    last_seen_camera = Column(String, default="Kamera Utama (Lobby)")

    is_known = Column(Boolean, default=False)
    is_watchlist = Column(Boolean, default=False)

    appearance_count = Column(Integer, default=1)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, index=True)

class FaceDetectionLog(Base):
    __tablename__ = "face_detection_logs"

    id = Column(String, primary_key=True, index=True)
    person_id = Column(String, index=True, nullable=True)
    camera_id = Column(String, index=True, nullable=False)
    camera_name = Column(String, nullable=False)

    confidence = Column(Float, default=0.0)
    image_crop_url = Column(String, nullable=False)
    bounding_box = Column(JSON, default=dict)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
