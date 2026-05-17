import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.error_log import ErrorLog
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.error_log import ErrorLogCreate, ErrorLogRead

router = APIRouter(prefix="/errors", tags=["errors"])


@router.post("/", response_model=ErrorLogRead, status_code=status.HTTP_201_CREATED)
async def log_error(
    data: ErrorLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = ErrorLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        created_at=data.created_at,
        context=data.context,
        message=data.message,
        details=data.details,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/", response_model=list[ErrorLogRead])
async def list_errors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's error logs, newest first (max 200)."""
    result = await db.execute(
        select(ErrorLog)
        .where(ErrorLog.user_id == current_user.id)
        .order_by(ErrorLog.created_at.desc())
        .limit(200)
    )
    return list(result.scalars().all())


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_errors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all error logs for the current user."""
    await db.execute(
        delete(ErrorLog).where(ErrorLog.user_id == current_user.id)
    )
    await db.commit()
