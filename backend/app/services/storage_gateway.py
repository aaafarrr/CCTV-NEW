import os
import json
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
import boto3
from botocore.config import Config
from app.core.config import settings

logger = logging.getLogger("cctv_new.storage_gateway")

CLOUD_CONFIG_PATH = os.path.join(settings.STORAGE_DIR, "cloud_config.json")

class ProductionStorageGateway:
    """
    Production Multi-Tier Cloud Storage Gateway using real boto3 client for
    AWS S3, Cloudflare R2, MinIO, or Wasabi object storage.
    """
    def __init__(self):
        self.s3_client = None
        self.policy: Dict[str, Any] = {}
        self.sync_jobs: List[Dict[str, Any]] = []
        self._load_config()
        self._init_s3_client()

    def _load_config(self):
        if os.path.exists(CLOUD_CONFIG_PATH):
            try:
                with open(CLOUD_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.policy = data.get("policy", {})
                    self.sync_jobs = data.get("sync_jobs", [])
                    return
            except Exception as e:
                logger.error(f"Error loading cloud_config.json: {e}")

        # Default policy
        self.policy = {
            "local_retention_days": 7,
            "cloud_retention_days": 90,
            "auto_sync_critical_events": True,
            "s3_bucket": settings.S3_BUCKET,
            "s3_endpoint_url": settings.S3_ENDPOINT_URL,
            "s3_region": settings.S3_REGION,
            "s3_prefix": settings.S3_PREFIX,
        }
        self.sync_jobs = []
        self._save_config()

    def _save_config(self):
        try:
            with open(CLOUD_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "policy": self.policy,
                    "sync_jobs": self.sync_jobs[:50]
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cloud_config.json: {e}")

    def _init_s3_client(self):
        bucket = self.policy.get("s3_bucket") or settings.S3_BUCKET
        endpoint = self.policy.get("s3_endpoint_url") or settings.S3_ENDPOINT_URL
        access_key = settings.S3_ACCESS_KEY
        secret_key = settings.S3_SECRET_KEY
        region = self.policy.get("s3_region") or settings.S3_REGION or "auto"

        if bucket and access_key and secret_key:
            try:
                cfg = Config(signature_version='s3v4', retries={'max_attempts': 3})
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=endpoint if endpoint else None,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region if region != "auto" else None,
                    config=cfg
                )
                logger.info(f"S3 Object Storage client connected (bucket: {bucket})")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
        else:
            self.s3_client = None

    def get_overview(self) -> Dict[str, Any]:
        snap_dir = settings.SNAPSHOT_DIR
        local_files = [f for f in os.listdir(snap_dir) if f.endswith(('.jpg', '.png', '.mp4'))] if os.path.exists(snap_dir) else []
        local_size_mb = sum(os.path.getsize(os.path.join(snap_dir, f)) for f in local_files) / (1024 * 1024)

        has_s3 = self.s3_client is not None
        bucket_name = self.policy.get("s3_bucket") or settings.S3_BUCKET or "(Belum Dikonfigurasi)"

        return {
            "s3_configured": has_s3,
            "s3_bucket": bucket_name,
            "s3_endpoint": self.policy.get("s3_endpoint_url") or settings.S3_ENDPOINT_URL or "AWS Default",
            "local_snapshots_count": len(local_files),
            "local_used_mb": round(local_size_mb, 2),
            "policy": self.policy,
            "recent_jobs": self.sync_jobs[:20]
        }

    def update_policy(self, new_policy: Dict[str, Any]) -> Dict[str, Any]:
        self.policy.update(new_policy)
        self._save_config()
        self._init_s3_client()
        return self.policy

    def upload_file_to_s3(self, local_path: str, remote_filename: str, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        file_size_mb = round(os.path.getsize(local_path) / (1024 * 1024), 2) if os.path.exists(local_path) else 0.0

        if not self.s3_client:
            job = {
                "id": job_id,
                "filename": remote_filename,
                "size_mb": file_size_mb,
                "status": "LOCAL_ONLY",
                "reason": "S3 Belum dikonfigurasi (.env atau Settings)",
                "timestamp": time.time()
            }
            self.sync_jobs.insert(0, job)
            self._save_config()
            return job

        bucket = self.policy.get("s3_bucket") or settings.S3_BUCKET
        prefix = self.policy.get("s3_prefix", "cctv")
        s3_key = f"{prefix}/{remote_filename}".replace("//", "/")

        try:
            extra_args = {}
            if remote_filename.endswith(".jpg") or remote_filename.endswith(".jpeg"):
                extra_args["ContentType"] = "image/jpeg"
            elif remote_filename.endswith(".mp4"):
                extra_args["ContentType"] = "video/mp4"

            if metadata:
                extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

            self.s3_client.upload_file(local_path, bucket, s3_key, ExtraArgs=extra_args)
            job = {
                "id": job_id,
                "filename": remote_filename,
                "s3_key": s3_key,
                "bucket": bucket,
                "size_mb": file_size_mb,
                "status": "COMPLETED",
                "timestamp": time.time()
            }
            logger.info(f"Successfully uploaded {local_path} to s3://{bucket}/{s3_key}")
        except Exception as e:
            logger.error(f"S3 upload error for {remote_filename}: {e}")
            job = {
                "id": job_id,
                "filename": remote_filename,
                "size_mb": file_size_mb,
                "status": "FAILED",
                "error": str(e),
                "timestamp": time.time()
            }

        self.sync_jobs.insert(0, job)
        self._save_config()
        return job

storage_gateway = ProductionStorageGateway()
