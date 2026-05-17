from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.user import User
from app.repositories.loan_repository import LoanRepository
from app.repositories.month_entry_repository import MonthEntryRepository
from app.routers.auth import get_current_user
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
    current_user: User = Depends(get_current_user),
):
    repo = MonthEntryRepository(db)
    if month_key:
        return await repo.get_all_for_month(month_key, current_user.id)
    if loan_id:
        # Verify the loan belongs to the current user before returning its entries
        loan_repo = LoanRepository(db)
        loan = await loan_repo.get_by_id(loan_id)
        if not loan or loan.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
        return await repo.get_all_for_loan(loan_id)
    return await repo.get_all(current_user.id)


@router.get("/months", response_model=list[str])
async def list_month_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all distinct month keys for the current user (newest first)."""
    repo = MonthEntryRepository(db)
    return await repo.get_all_month_keys(current_user.id)


@router.get("/{entry_id}", response_model=MonthEntryRead)
async def get_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = MonthEntryRepository(db)
    entry = await repo.get_by_id_for_user(entry_id, current_user.id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return entry


@router.post("/", response_model=MonthEntryRead, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: MonthEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify the target loan belongs to the current user
    loan_repo = LoanRepository(db)
    loan = await loan_repo.get_by_id(data.loan_id)
    if not loan or loan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    repo = MonthEntryRepository(db)
    entry = await repo.create(data)
    await db.commit()
    return entry


@router.post("/upsert", response_model=MonthEntryRead)
async def upsert_entry(
    data: MonthEntryUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Insert or update a single entry by (loan_id, month_key)."""
    # Verify the target loan belongs to the current user
    loan_repo = LoanRepository(db)
    loan = await loan_repo.get_by_id(data.loan_id)
    if not loan or loan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    repo = MonthEntryRepository(db)
    entry = await repo.upsert(data)
    await db.commit()
    return entry


@router.patch("/{entry_id}", response_model=MonthEntryRead)
async def update_entry(
    entry_id: str,
    data: MonthEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = MonthEntryRepository(db)
    entry = await repo.get_by_id_for_user(entry_id, current_user.id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    updated = await repo.update(entry_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    await db.commit()
    return updated


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = MonthEntryRepository(db)
    entry = await repo.get_by_id_for_user(entry_id, current_user.id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    deleted = await repo.delete(entry_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    await db.commit()
