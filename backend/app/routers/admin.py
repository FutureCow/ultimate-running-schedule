from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.models.plan import Plan
from app.routers.deps import get_current_user
from app.services import auth_service
from app.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class AdminUserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool
    tier: str
    plan_count: int
    created_at: str

    class Config:
        from_attributes = True


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    tier: Optional[str] = None


class AdminResetPassword(BaseModel):
    new_password: str


class AdminSettings(BaseModel):
    registration_open: Optional[bool] = None


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    out = []
    for u in users:
        plan_result = await db.execute(select(func.count()).where(Plan.user_id == u.id))
        plan_count = plan_result.scalar() or 0
        out.append({
            "id": u.id,
            "email": u.email,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
            "tier": u.tier,
            "plan_count": plan_count,
            "created_at": u.created_at.isoformat(),
        })
    return out


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.tier is not None:
        if payload.tier not in ("base", "tempo", "elite"):
            raise HTTPException(status_code=400, detail="Ongeldige tier")
        user.tier = payload.tier
    await db.commit()
    return {"id": user.id, "email": user.email, "is_active": user.is_active, "is_admin": user.is_admin, "tier": user.tier}


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    payload: AdminResetPassword,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = auth_service.hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.commit()
    return {"detail": "Password reset"}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()


@router.get("/settings")
async def get_admin_settings(_: User = Depends(get_admin_user)):
    return {"registration_open": settings.REGISTRATION_OPEN}


@router.patch("/settings")
async def update_admin_settings(
    payload: AdminSettings,
    _: User = Depends(get_admin_user),
):
    if payload.registration_open is not None:
        settings.REGISTRATION_OPEN = payload.registration_open
    return {"registration_open": settings.REGISTRATION_OPEN}
