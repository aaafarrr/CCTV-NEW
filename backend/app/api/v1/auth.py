from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.user import User
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
    validate_safe_id,
    login_limiter
)

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
    full_name: str

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=5, max_length=120)
    role: str = "OPERATOR"

class SetupAdminRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=5, max_length=120)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None

@router.get("/status")
async def check_system_setup_status(db: AsyncSession = Depends(get_db)):
    """Check whether the system has an administrator registered (needs initial setup)"""
    result = await db.execute(select(User).limit(1))
    has_user = result.scalars().first() is not None
    return {
        "is_configured": has_user,
        "needs_initial_setup": not has_user
    }

@router.post("/setup-admin", response_model=Token)
async def setup_initial_admin(payload: SetupAdminRequest, db: AsyncSession = Depends(get_db)):
    """Creates the root administrator on initial boot when no users exist."""
    existing = (await db.execute(select(User).limit(1))).scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup awal sudah selesai. Silakan login menggunakan akun terdaftar."
        )

    uname = validate_safe_id(payload.username, "Username")
    admin_user = User(
        username=uname,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        email=payload.email,
        role="ADMIN",
        is_active=True
    )
    db.add(admin_user)
    await db.commit()

    token = create_access_token(data={"sub": admin_user.username, "role": "ADMIN", "full_name": admin_user.full_name})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": admin_user.username,
        "role": admin_user.role,
        "full_name": admin_user.full_name
    }

@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{form_data.username}_{client_ip}"
    login_limiter.check(rate_key)

    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        login_limiter.fail(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau Password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun dinonaktifkan")

    login_limiter.reset(rate_key)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "full_name": user.full_name}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name
    }

@router.get("/me")
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

@router.get("/users")
async def list_users(
    _: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).order_by(User.created_at.asc()))
    users = result.scalars().all()
    return [
        {
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active
        }
        for u in users
    ]

@router.post("/users")
async def create_user(
    payload: UserCreate,
    _: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    uname = validate_safe_id(payload.username, "Username")
    existing = (await db.execute(select(User).where(User.username == uname))).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Username sudah terdaftar")

    new_user = User(
        username=uname,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        email=payload.email,
        role=payload.role if payload.role in ("ADMIN", "OPERATOR", "VIEWER") else "OPERATOR",
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    return {"status": "success", "message": f"Akun {uname} berhasil dibuat"}

@router.put("/users/{username}")
async def update_user(
    username: str,
    payload: UserUpdate,
    _: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    uname = validate_safe_id(username, "Username")
    user = (await db.execute(select(User).where(User.username == uname))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")

    if payload.full_name:
        user.full_name = payload.full_name
    if payload.email:
        user.email = payload.email
    if payload.role in ("ADMIN", "OPERATOR", "VIEWER"):
        user.role = payload.role
    if payload.password:
        user.hashed_password = hash_password(payload.password)

    await db.commit()
    return {"status": "success", "message": f"Akun {uname} berhasil diperbarui"}

@router.delete("/users/{username}")
async def delete_user(
    username: str,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    uname = validate_safe_id(username, "Username")
    if uname == current_admin.get("username"):
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus akun Anda sendiri")

    user = (await db.execute(select(User).where(User.username == uname))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")

    await db.delete(user)
    await db.commit()
    return {"status": "success", "message": f"Akun {uname} berhasil dihapus"}
