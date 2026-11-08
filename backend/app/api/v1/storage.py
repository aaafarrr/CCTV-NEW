from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.services.storage_gateway import storage_gateway
from app.core.security import validate_safe_id, get_current_user, require_admin

router = APIRouter(prefix="/storage", tags=["Multi-Cloud Storage Pool (Clospol)"])

class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    type: str = Field(..., description="GOOGLE_DRIVE, ONEDRIVE, S3_COMPATIBLE, LOCAL_DISK")
    endpoint: str = Field(..., min_length=3, max_length=250)
    tier: str = Field(default="WARM (Tier 2)")
    quota_gb: float = Field(default=1000.0, gt=0)

class PolicyUpdate(BaseModel):
    local_retention_hours: int = Field(default=48, ge=1, le=720)
    cloud_retention_days: int = Field(default=90, ge=7, le=3650)
    pre_event_buffer_sec: int = Field(default=5, ge=1, le=30)
    post_event_buffer_sec: int = Field(default=10, ge=1, le=60)
    auto_tiering_enabled: bool = True
    sync_on_severity: List[str] = ["CRITICAL", "WARNING"]
    routing_strategy: str = "WEIGHTED_FAILOVER"

class SyncTriggerRequest(BaseModel):
    camera_name: str = "Semua Kamera Aktif"
    reason: str = "Sinkronisasi Instan"

@router.get("/overview")
async def get_storage_overview() -> Dict[str, Any]:
    return storage_gateway.get_pool_overview()

@router.post("/providers")
async def add_storage_provider(payload: ProviderCreate, _: Dict[str, Any] = Depends(require_admin)):
    return storage_gateway.add_provider(
        name=payload.name,
        ptype=payload.type,
        endpoint=payload.endpoint,
        tier=payload.tier,
        quota_gb=payload.quota_gb
    )

@router.put("/providers/{provider_id}/toggle")
async def toggle_storage_provider(provider_id: str, _: Dict[str, Any] = Depends(get_current_user)):
    pid = validate_safe_id(provider_id, "Provider ID")
    try:
        return storage_gateway.toggle_provider(pid)
    except KeyError:
        raise HTTPException(status_code=404, detail="Storage provider tidak ditemukan")

@router.delete("/providers/{provider_id}")
async def delete_storage_provider(provider_id: str, _: Dict[str, Any] = Depends(require_admin)):
    pid = validate_safe_id(provider_id, "Provider ID")
    if pid == "prov_local_nvme":
        raise HTTPException(status_code=400, detail="Local NVMe Buffer utama tidak dapat dihapus")
    if not storage_gateway.delete_provider(pid):
        raise HTTPException(status_code=404, detail="Storage provider tidak ditemukan")
    return {"status": "success", "message": f"Provider {pid} berhasil dihapus"}

@router.put("/policy")
async def update_storage_policy(payload: PolicyUpdate, _: Dict[str, Any] = Depends(get_current_user)):
    return storage_gateway.update_policy(payload.model_dump())

@router.post("/sync")
async def trigger_manual_sync(payload: SyncTriggerRequest, _: Dict[str, Any] = Depends(get_current_user)):
    return storage_gateway.trigger_cloud_sync(camera_name=payload.camera_name, reason=payload.reason)

