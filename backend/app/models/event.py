from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from app.core.database import Base

class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String, primary_key=True, index=True)
    camera_id = Column(String, index=True, nullable=False)
    camera_name = Column(String, nullable=False)

    event_type = Column(String, index=True, nullable=False)
    severity = Column(String, default="WARNING")
    description = Column(Text, nullable=False)
    ai_summary = Column(Text, nullable=True)

    snapshot_url = Column(String, nullable=True)
    clip_url = Column(String, nullable=True)
    cloud_synced = Column(Integer, default=0)

    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class TrafficCountLog(Base):
    __tablename__ = "traffic_count_logs"

    id = Column(String, primary_key=True, index=True)
    camera_id = Column(String, index=True, nullable=False)

    people_in = Column(Integer, default=0)
    people_out = Column(Integer, default=0)
    vehicles_in = Column(Integer, default=0)
    vehicles_out = Column(Integer, default=0)

    vehicle_breakdown = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
