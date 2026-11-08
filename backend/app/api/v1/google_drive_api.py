from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.services.google_drive import clospol_gdrive
from app.core.security import get_current_user

router = APIRouter(prefix="/google-drive", tags=["Google Drive Storage"])

class GoogleDriveConfigUpdate(BaseModel):
    client_id: str = Field(...)
    client_secret: str = Field(...)
    refresh_token: str = Field(...)
    root_folder_name: str = Field(default="CCTV Recordings")

@router.get("/status")
async def get_google_drive_status(_: Dict[str, Any] = Depends(get_current_user)):
    quota = clospol_gdrive.get_quota()
    return {
        "is_configured": clospol_gdrive.is_configured(),
        "root_folder": clospol_gdrive.root_folder_name,
        "quota": quota
    }

@router.post("/configure")
async def configure_google_drive(payload: GoogleDriveConfigUpdate, _: Dict[str, Any] = Depends(get_current_user)):
    clospol_gdrive.update_credentials(
        client_id=payload.client_id,
        client_secret=payload.client_secret,
        refresh_token=payload.refresh_token,
        root_folder=payload.root_folder_name
    )
    # Test connection
    quota = clospol_gdrive.get_quota()
    if not quota.get("configured"):
        raise HTTPException(status_code=400, detail=f"Koneksi Google Drive gagal: {quota.get('error', 'Kredensial tidak valid')}")

    return {
        "status": "success",
        "message": "Koneksi Google Drive berhasil dikonfigurasi",
        "quota": quota
    }

