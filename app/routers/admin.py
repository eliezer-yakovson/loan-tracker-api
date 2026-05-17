from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="אין הרשאות אדמין")
    return current_user


@router.get("/users", summary="רשימת כל המשתמשים (אדמין בלבד)")
async def list_users(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "created_at": u.created_at,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
        }
        for u in users
    ]


@router.patch("/users/{user_id}/toggle-active", summary="הפעל/השבת משתמש")
async def toggle_user_active(
    user_id: str,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="לא ניתן לשנות סטטוס של עצמך")
    user.is_active = not user.is_active
    await session.commit()
    return {"id": user.id, "is_active": user.is_active}
