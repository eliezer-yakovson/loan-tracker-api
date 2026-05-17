from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.month_entry import MonthEntry
from app.repositories.category_repository import CategoryRepository
from app.repositories.loan_repository import LoanRepository
from app.repositories.month_entry_repository import MonthEntryRepository
from app.schemas.sync import AppStateIn, AppStateOut

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/", response_model=AppStateOut)
async def push_state(data: AppStateIn, db: AsyncSession = Depends(get_db)):
    """
    Bulk-upsert the full app state sent by the React client, then return the
    refreshed state from the database.

    Order matters: categories → loans → month_entries (FK chain).
    """
    cat_repo = CategoryRepository(db)
    loan_repo = LoanRepository(db)
    entry_repo = MonthEntryRepository(db)

    for cat in data.categories:
        await cat_repo.upsert(cat)

    for loan in data.loans:
        await loan_repo.upsert(loan)

    for entry in data.month_entries:
        await entry_repo.upsert(entry)

    await db.commit()

    # Return the full state as stored in the DB
    all_entries_result = await db.execute(
        select(MonthEntry).order_by(MonthEntry.month_key, MonthEntry.loan_id)
    )
    all_entries = list(all_entries_result.scalars().all())

    return AppStateOut(
        selected_month=data.selected_month,
        categories=await cat_repo.get_all(),
        loans=await loan_repo.get_all(),
        month_entries=all_entries,
    )


@router.get("/", response_model=AppStateOut)
async def pull_state(
    selected_month: str = Query(..., description="Currently selected month (YYYY-MM)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Pull the complete app state from the database.
    The client passes its current selected_month so the response mirrors AppState.
    """
    cat_repo = CategoryRepository(db)
    loan_repo = LoanRepository(db)

    all_entries_result = await db.execute(
        select(MonthEntry).order_by(MonthEntry.month_key, MonthEntry.loan_id)
    )
    all_entries = list(all_entries_result.scalars().all())

    return AppStateOut(
        selected_month=selected_month,
        categories=await cat_repo.get_all(),
        loans=await loan_repo.get_all(),
        month_entries=all_entries,
    )
