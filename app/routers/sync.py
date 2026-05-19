from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.category import Category
from app.models.loan import Loan
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
    Full-state replacement: upsert what the client has, then delete anything
    the client no longer has (reconcile), then return the refreshed state.

    Order matters: categories → loans → month_entries (FK chain).
    """
    user_id = current_user.id
    cat_repo = CategoryRepository(db)
    loan_repo = LoanRepository(db)
    entry_repo = MonthEntryRepository(db)

    # ── Step 1: Upsert incoming records ────────────────────────────────────────
    for cat in data.categories:
        await cat_repo.upsert(cat, user_id)

    # Build the set of category IDs this user actually owns after the upserts above.
    # Any loan whose category_id is not in this set references a foreign category and
    # must be dropped — otherwise a client could create a cross-user FK link.
    user_cats_after_upsert = await cat_repo.get_all(user_id)
    valid_cat_ids = {cat.id for cat in user_cats_after_upsert}

    for loan in data.loans:
        if loan.category_id not in valid_cat_ids:
            # Silently skip — raising would expose information about foreign IDs.
            continue
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

    # ── Step 2: Reconcile — delete records absent from the client payload ──────
    # This turns every push into a full-state replacement so that items deleted
    # while offline (or when the fire-and-forget DELETE call was skipped / failed)
    # are removed before the next pull, preventing "ghost" re-appearances.
    incoming_cat_ids = {cat.id for cat in data.categories}
    incoming_loan_ids = {loan.id for loan in data.loans}

    # Delete orphaned categories. FK cascade removes their loans and month_entries.
    # The user_id guard ensures we never touch another user's data.
    if incoming_cat_ids:
        await db.execute(
            delete(Category)
            .where(Category.user_id == user_id)
            .where(Category.id.notin_(incoming_cat_ids))
        )
    else:
        # Empty payload → remove all of this user's categories.
        await db.execute(delete(Category).where(Category.user_id == user_id))

    # Delete orphaned loans. FK cascade removes their month_entries.
    # Loans under deleted categories are already gone via the cascade above;
    # this handles loans deleted independently of their category.
    if incoming_loan_ids:
        await db.execute(
            delete(Loan)
            .where(Loan.user_id == user_id)
            .where(Loan.id.notin_(incoming_loan_ids))
        )
    else:
        await db.execute(delete(Loan).where(Loan.user_id == user_id))

    await db.commit()

    # ── Step 3: Return the reconciled state ────────────────────────────────────
    final_cats = await cat_repo.get_all(user_id)
    final_loans = await loan_repo.get_all(user_id)
    final_loan_ids = [loan.id for loan in final_loans]
    all_entries = await _get_entries_for_user(db, final_loan_ids)

    return AppStateOut(
        selected_month=data.selected_month,
        categories=final_cats,
        loans=final_loans,
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
