from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.month_entry import MonthEntry
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.loan_repository import LoanRepository
from app.repositories.month_entry_repository import MonthEntryRepository
from app.routers.auth import get_current_user
from app.schemas.sync import AppStateIn, AppStateOut

router = APIRouter(prefix="/sync", tags=["sync"])


async def _get_entries_for_user(db: AsyncSession, user_loan_ids: list[str]) -> list[MonthEntry]:
    if not user_loan_ids:
        return []
    result = await db.execute(
        select(MonthEntry)
        .where(MonthEntry.loan_id.in_(user_loan_ids))
        .order_by(MonthEntry.month_key, MonthEntry.loan_id)
    )
    return list(result.scalars().all())


@router.post("/", response_model=AppStateOut)
async def push_state(
    data: AppStateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk-upsert the full app state sent by the React client, then return the
    refreshed state from the database.

    Order matters: categories → loans → month_entries (FK chain).
    """
    user_id = current_user.id
    cat_repo = CategoryRepository(db)
    loan_repo = LoanRepository(db)
    entry_repo = MonthEntryRepository(db)

    for cat in data.categories:
        await cat_repo.upsert(cat, user_id)

    for loan in data.loans:
        await loan_repo.upsert(loan, user_id)

    # Build the set of loan IDs that genuinely belong to this user AFTER the
    # loan upserts above, so newly-synced loans are included.
    user_loans_after_upsert = await loan_repo.get_all(user_id)
    user_loan_ids_set = {loan.id for loan in user_loans_after_upsert}

    for entry in data.month_entries:
        if entry.loan_id not in user_loan_ids_set:
            # Silently skip entries that reference loans owned by other users.
            # Raising here would expose information about foreign IDs, so we drop them.
            continue
        await entry_repo.upsert(entry)

    await db.commit()

    user_loan_ids = list(user_loan_ids_set)
    all_entries = await _get_entries_for_user(db, user_loan_ids)

    return AppStateOut(
        selected_month=data.selected_month,
        categories=await cat_repo.get_all(user_id),
        loans=user_loans_after_upsert,
        month_entries=all_entries,
    )


@router.get("/", response_model=AppStateOut)
async def pull_state(
    selected_month: str = Query(..., description="Currently selected month (YYYY-MM)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pull the complete app state from the database for the current user.
    """
    user_id = current_user.id
    cat_repo = CategoryRepository(db)
    loan_repo = LoanRepository(db)

    user_loans = await loan_repo.get_all(user_id)
    user_loan_ids = [loan.id for loan in user_loans]
    all_entries = await _get_entries_for_user(db, user_loan_ids)

    return AppStateOut(
        selected_month=selected_month,
        categories=await cat_repo.get_all(user_id),
        loans=user_loans,
        month_entries=all_entries,
    )
