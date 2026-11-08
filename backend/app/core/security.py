import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|mp4)$")
PBKDF2_ITERATIONS = 310_000
VALID_ROLES = ("ADMIN", "OPERATOR", "VIEWER")


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 with a random per-user salt, stored as algo$iter$salt$hash."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algo, iterations, salt, expected = hashed_password.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(dk.hex(), expected)
    except (ValueError, AttributeError):
        return False


class LoginRateLimiter:
    """Lock a username+IP pair for LOCK_SECONDS after MAX_FAILURES failed logins."""
    MAX_FAILURES = 5
    LOCK_SECONDS = 300

    def __init__(self):
        self._failures: Dict[str, list] = {}

    def check(self, key: str):
        fails = [t for t in self._failures.get(key, []) if time.time() - t < self.LOCK_SECONDS]
        self._failures[key] = fails
        if len(fails) >= self.MAX_FAILURES:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Terlalu banyak percobaan login gagal. Coba lagi dalam 5 menit.",
            )

    def fail(self, key: str):
        self._failures.setdefault(key, []).append(time.time())

    def reset(self, key: str):
        self._failures.pop(key, None)


login_limiter = LoginRateLimiter()


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
    parsed = urlparse(url)
    if parsed.scheme not in ("rtsp", "rtsps", "http", "https") or not parsed.hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL Stream harus berupa rtsp://, rtsps://, http:// atau https:// dengan host yang valid"
        )
    # Admin-only input, so local relays (go2rtc on 127.0.0.1) stay allowed; only cloud metadata is blocked
    if parsed.hostname.lower() in ("169.254.169.254", "metadata.google.internal", "100.100.100.200"):
        raise HTTPException(status_code=400, detail="Host stream tidak diizinkan")
    return url


def mask_stream_url(url: str) -> str:
    """Hide the password part of rtsp://user:pass@host so credentials never reach the browser."""
    parsed = urlparse(url or "")
    if parsed.password:
        return url.replace(f":{parsed.password}@", ":***@", 1)
    return url


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(
    header_token: Optional[str] = Depends(oauth2_scheme),
    token: Optional[str] = Query(None, include_in_schema=False),
) -> Dict[str, Any]:
    """Accept Bearer header, or ?token= for <img>/MJPEG tags that cannot send headers."""
    raw = header_token or token
    if not raw:
        raise _unauthorized("Autentikasi diperlukan")
    try:
        payload = jwt.decode(raw, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise _unauthorized("Token tidak valid atau telah kedaluwarsa")
    username = payload.get("sub")
    if not username:
        raise _unauthorized("Token tidak valid")

    # Re-read role from DB so deleted/demoted users lose access immediately
    with sqlite3.connect(settings.DATABASE_PATH, timeout=5.0) as conn:
        row = conn.execute(
            "SELECT username, full_name, role, is_active FROM users WHERE username = ?", (username,)
        ).fetchone()
    if not row or not row[3]:
        raise _unauthorized("Akun tidak ditemukan atau nonaktif")
    return {"username": row[0], "full_name": row[1], "role": row[2], "is_active": bool(row[3])}


async def require_operator(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") not in ("ADMIN", "OPERATOR"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak: membutuhkan hak akses Operator")
    return current_user


async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak: membutuhkan hak akses Administrator")
    return current_user
