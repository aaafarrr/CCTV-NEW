from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from app.core.database import Base

class GoogleDriveConfig(Base):
    """
    Connected Google Drive storage settings matching Clospol ConnectedAccount & StorageAccount
    """
    __tablename__ = "google_drive_configs"

    id = Column(String, primary_key=True, default="default")
    client_id = Column(String, nullable=True)
    client_secret = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    root_folder_name = Column(String, default="CCTV Recordings")
    root_folder_id = Column(String, nullable=True)

    is_connected = Column(Boolean, default=False)
    total_bytes = Column(Integer, default=0)
    used_bytes = Column(Integer, default=0)
    available_bytes = Column(Integer, default=0)
    last_synced_at = Column(DateTime, nullable=True)

