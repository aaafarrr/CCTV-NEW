import os
import io
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
from app.core.config import settings

logger = logging.getLogger("clospol.google_drive")

class ClospolGoogleDriveService:
    """
    Python implementation of Clospol's GoogleDriveService.
    Supports token refresh, app folder hierarchy (Root -> Camera Name -> YYYY-MM),
    file uploading with automatic mime-type detection, and storage quota sync.
    """
    GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.refresh_token = settings.GOOGLE_REFRESH_TOKEN
        self.root_folder_name = settings.GOOGLE_ROOT_FOLDER
        self.cached_folder_ids: Dict[str, str] = {}

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def update_credentials(self, client_id: str, client_secret: str, refresh_token: str, root_folder: str = "CCTV Recordings"):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.refresh_token = refresh_token.strip()
        self.root_folder_name = root_folder.strip() or "CCTV Recordings"
        self.cached_folder_ids.clear()

    def get_drive_service(self):
        if not self.is_configured():
            raise ValueError("Google Drive OAuth credentials are not configured.")

        creds = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )

        if not creds.valid:
            creds.refresh(Request())

        return build("drive", "v3", credentials=creds)

    def get_quota(self) -> Dict[str, Any]:
        """Fetch Google Drive quota (total, used, free) matching Clospol syncGoogleQuota"""
        if not self.is_configured():
            return {
                "configured": False,
                "total_bytes": 0,
                "used_bytes": 0,
                "available_bytes": 0,
                "used_percentage": 0.0
            }

        try:
            service = self.get_drive_service()
            about = service.about().get(fields="storageQuota,user").execute()
            quota = about.get("storageQuota", {})
            total = int(quota.get("limit", 0)) if quota.get("limit") else None
            used = int(quota.get("usage", 0))
            available = (total - used) if total is not None else None
            pct = round((used / total * 100), 2) if total else 0.0

            return {
                "configured": True,
                "user": about.get("user", {}).get("displayName", "Google User"),
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "used_percentage": pct
            }
        except Exception as e:
            logger.error(f"Error fetching Google Drive quota: {e}")
            return {
                "configured": False,
                "error": str(e),
                "total_bytes": 0,
                "used_bytes": 0,
                "available_bytes": 0
            }

    def _get_or_create_folder(self, service, folder_name: str, parent_id: Optional[str] = None) -> str:
        cache_key = f"{parent_id or 'root'}_{folder_name}"
        if cache_key in self.cached_folder_ids:
            return self.cached_folder_ids[cache_key]

        safe_name = folder_name.replace("'", "\\'")
        query = f"name = '{safe_name}' and mimeType = '{self.GOOGLE_FOLDER_MIME}' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        else:
            query += " and 'root' in parents"

        response = service.files().list(q=query, spaces="drive", fields="files(id, name)", pageSize=1).execute()
        files = response.get("files", [])
        if files:
            folder_id = files[0]["id"]
            self.cached_folder_ids[cache_key] = folder_id
            return folder_id

        # Create new folder
        meta = {
            "name": folder_name,
            "mimeType": self.GOOGLE_FOLDER_MIME,
            "parents": [parent_id] if parent_id else ["root"]
        }
        folder = service.files().create(body=meta, fields="id").execute()
        folder_id = folder.get("id")
        self.cached_folder_ids[cache_key] = folder_id
        return folder_id

    def get_or_create_cctv_path(self, service, camera_name: str) -> str:
        """
        Builds the Clospol folder structure:
        Root Folder (e.g. 'CCTV Recordings') -> Camera Name -> YYYY-MM
        """
        root_id = self._get_or_create_folder(service, self.root_folder_name)
        cam_id = self._get_or_create_folder(service, camera_name, root_id)
        year_month = datetime.now().strftime("%Y-%m")
        month_id = self._get_or_create_folder(service, year_month, cam_id)
        return month_id

    def upload_cctv_file(self, local_path: str, file_name: str, camera_name: str, mime_type: str = "video/mp4") -> Dict[str, Any]:
        """Uploads snapshot or video recording to Google Drive under the hierarchical folder structure"""
        if not self.is_configured():
            raise ValueError("Google Drive is not configured")

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")

        service = self.get_drive_service()
        dest_folder_id = self.get_or_create_cctv_path(service, camera_name)

        file_metadata = {
            "name": file_name,
            "parents": [dest_folder_id]
        }

        media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
        uploaded = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink, webContentLink").execute()

        file_id = uploaded.get("id")
        view_link = uploaded.get("webViewLink")

        logger.info(f"Successfully uploaded {file_name} to Google Drive (ID: {file_id})")
        return {
            "file_id": file_id,
            "web_view_link": view_link,
            "download_link": uploaded.get("webContentLink")
        }

clospol_gdrive = ClospolGoogleDriveService()

