from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.repositories.month_entry_repository import MonthEntryRepository
from app.schemas.month_entry import (
    MonthEntryCreate,
    MonthEntryRead,
    MonthEntryUpdate,
    MonthEntryUpsert,
)

router = APIRouter(prefix="/month-entries", tags=["month_entries"])


@router.get("/", response_model=list[MonthEntryRead])
async def list_entries(
    month_key: str | None = Query(default=None, description="Filter by month (YYYY-MM)"),
    loan_id: str | None = Query(default=None, description="Filter by loan"),
    db: AsyncSession = Depends(get_db),
):
    repo = MonthEntryRepository(db)
    if month_key:
        return await repo.get_all_for_month(month_key)
    if loan_id:
        return await repo.get_all_for_loan(loan_id)
    return await repo.get_all()


@router.get("/months", response_model=list[str])
async def list_month_keys(db: AsyncSession = Depends(get_db)):
    """Return all distinct month keys that have at least one entry (newest first)."""
    repo = MonthEntryRepository(db)
    return await repo.get_all_month_keys()


@router.get("/{entry_id}", response_model=MonthEntryRead)
async def get_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    repo = MonthEntryRepository(db)
    entry = await repo.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return entry


@router.post("/", response_model=MonthEntryRead, status_code=status.HTTP_201_CREATED)
async def create_entry(data: MonthEntryCreate, db: AsyncSession = Depends(get_db)):
    repo = MonthEntryRepository(db)
    entry = await repo.create(data)
    await db.commit()
    return entry


@router.post("/upsert", response_model=MonthEntryRead)
async def upsert_entry(data: MonthEntryUpsert, db: AsyncSession = Depends(get_db)):
    """Insert or update a single entry by (loan_id, month_key)."""
    repo = MonthEntryRepository(db)
    entry = await repo.upsert(data)
    await db.commit()
    return entry


@router.patch("/{entry_id}", response_model=MonthEntryRead)
async def update_entry(
    entry_id: str,
    data: MonthEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    repo = MonthEntryRepository(db)
    entry = await repo.update(entry_id, data)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    await db.commit()
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    repo = MonthEntryRepository(db)
    deleted = await repo.delete(entry_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    await db.commit()
