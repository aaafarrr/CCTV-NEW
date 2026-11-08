import hashlib
import hmac
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|mp4)$")
ALLOWED_SYNTHETIC_STREAMS = {
    "synthetic_lobby",
    "synthetic_parking",
    "synthetic_gate",
    "synthetic_warehouse",
    "",
}

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 (120,000 iterations)"""
    salt = settings.SECRET_KEY[:24].encode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return dk.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time password comparison to prevent timing attacks"""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

def validate_safe_id(value: str, field_name: str = "ID") -> str:
    """Validate identifier at trust boundary to prevent path traversal or injection"""
    if not value or not SAFE_ID_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} tidak valid (hanya huruf, angka, '-' dan '_')"
        )
    return value

def validate_safe_filename(filename: str) -> str:
    """Validate filename at trust boundary to prevent directory traversal"""
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nama file tidak valid")
    if not SAFE_FILENAME_PATTERN.match(filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Format nama file tidak diizinkan")
    return filename

def validate_stream_url(stream_url: str) -> str:
    """Validate camera stream URL at trust boundary (prevent SSRF & arbitrary local file read)"""
    url = (stream_url or "").strip()
    if url in ALLOWED_SYNTHETIC_STREAMS:
        return url
    parsed = urlparse(url)
    if parsed.scheme in ("rtsp", "rtsps", "http", "https"):
        host = (parsed.hostname or "").lower()
        if host in ("169.254.169.254", "metadata.google.internal"):
            raise HTTPException(status_code=400, detail="Alamat host metadata cloud tidak diizinkan")
        return url
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="URL Stream harus menggunakan protokol rtsp://, rtsps://, http://, atau mode synthetic_*"
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Dict[str, Any]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan: Token Bearer tidak ditemukan",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token kredensial tidak valid")
        return {
            "username": username,
            "role": payload.get("role", "OPERATOR"),
            "full_name": payload.get("full_name", username),
            "is_active": True
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token keamanan tidak valid atau telah kedaluwarsa",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: membutuhkan hak akses Administrator"
        )
    return current_user
