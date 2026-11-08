from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
    validate_safe_id,
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
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=5, max_length=120)
    role: str = "OPERATOR"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None

async def seed_initial_users():
    """Ensure default admin & operator accounts are persisted in SQLite"""
    async with AsyncSessionLocal() as db:
        defaults = [
            {
                "username": "admin",
                "hashed_password": hash_password("admin123"),
                "full_name": "System Administrator",
                "email": "admin@cctv-enterprise.local",
                "role": "ADMIN",
            },
            {
                "username": "operator",
                "hashed_password": hash_password("operator123"),
                "full_name": "Petugas Ruang Kontrol",
                "email": "operator@cctv-enterprise.local",
                "role": "OPERATOR",
            },
        ]
        for d in defaults:
            existing = (await db.execute(select(User).where(User.username == d["username"]))).scalars().first()
            if not existing:
                db.add(User(**d, is_active=True))
        await db.commit()

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau Password tidak sesuai",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
    _: Dict[str, Any] = Depends(get_current_user),
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
    return {"status": "success", "message": f"Akun {uname} berhasil disimpan ke database"}

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
    _: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    uname = validate_safe_id(username, "Username")
    if uname == "admin":
        raise HTTPException(status_code=400, detail="Akun Administrator utama tidak dapat dihapus")
    user = (await db.execute(select(User).where(User.username == uname))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")

    await db.delete(user)
    await db.commit()
    return {"status": "success", "message": f"Akun {uname} dihapus dari database"}
