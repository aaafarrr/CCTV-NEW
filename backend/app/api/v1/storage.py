from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.services.storage_gateway import storage_gateway
from app.core.security import get_current_user, require_admin

router = APIRouter(prefix="/storage", tags=["S3 Cloud Storage Gateway"])

class PolicyUpdate(BaseModel):
    local_retention_days: int = Field(default=7, ge=1, le=365)
    cloud_retention_days: int = Field(default=90, ge=7, le=3650)
    auto_sync_critical_events: bool = True
    s3_bucket: str = Field(default="")
    s3_endpoint_url: str = Field(default="")
    s3_region: str = Field(default="auto")
    s3_prefix: str = Field(default="cctv")

@router.get("/overview")
async def get_storage_overview(_: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return storage_gateway.get_overview()

@router.put("/policy")
async def update_storage_policy(payload: PolicyUpdate, _: Dict[str, Any] = Depends(require_admin)):
    return storage_gateway.update_policy(payload.model_dump())
