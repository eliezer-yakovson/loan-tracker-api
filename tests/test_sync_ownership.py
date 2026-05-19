"""Tests for cross-user ownership protection in the sync route.

Verifies that push_state silently drops loans whose category_id references a
category that does not belong to the current user.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(user_id: str = "user-1") -> MagicMock:
    from app.models.user import User

    u = MagicMock(spec=User)
    u.id = user_id
    return u


def _make_category(cat_id: str) -> MagicMock:
    c = MagicMock()
    c.id = cat_id
    c.name = f"Category {cat_id}"
    return c


def _make_loan_create(loan_id: str, category_id: str):
    from app.schemas.loan import LoanCreate

    return LoanCreate(
        id=loan_id,
        category_id=category_id,
        name=f"Loan {loan_id}",
        lender_name="Test Bank",
        original_amount=Decimal("1000"),
        monthly_amount=Decimal("100"),
        total_payments=10,
        taken_date="2024-01-01",
        monthly_due_day=1,
    )


def _make_category_create(cat_id: str):
    from app.schemas.category import CategoryCreate

    return CategoryCreate(id=cat_id, name=f"Cat {cat_id}")


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_push_state_drops_loan_with_foreign_category():
    """Loans whose category_id is not owned by the current user must be silently dropped."""
    from app.routers.sync import push_state
    from app.schemas.sync import AppStateIn

    user = _make_user("user-1")

    # User owns only cat-A
    owned_cat = _make_category("cat-A")

    mock_cat_repo = AsyncMock()
    mock_cat_repo.upsert = AsyncMock()
    mock_cat_repo.get_all = AsyncMock(return_value=[owned_cat])

    mock_loan_repo = AsyncMock()
    mock_loan_repo.upsert = AsyncMock()
    mock_loan_repo.get_all = AsyncMock(return_value=[])

    mock_entry_repo = AsyncMock()

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    data = AppStateIn(
        selected_month="2024-01",
        categories=[_make_category_create("cat-A")],
        loans=[
            _make_loan_create("loan-good", "cat-A"),    # owned category — should upsert
            _make_loan_create("loan-foreign", "cat-B"),  # foreign category — must be dropped
        ],
        month_entries=[],
    )

    with (
        patch("app.routers.sync.CategoryRepository", return_value=mock_cat_repo),
        patch("app.routers.sync.LoanRepository", return_value=mock_loan_repo),
        patch("app.routers.sync.MonthEntryRepository", return_value=mock_entry_repo),
        patch("app.routers.sync._get_entries_for_user", new=AsyncMock(return_value=[])),
    ):
        await push_state(data=data, db=mock_db, current_user=user)

    upserted_ids = [call.args[0].id for call in mock_loan_repo.upsert.call_args_list]
    assert "loan-good" in upserted_ids, "Loan with owned category should be upserted"
    assert "loan-foreign" not in upserted_ids, "Loan with foreign category must be silently dropped"


@pytest.mark.asyncio
async def test_push_state_allows_all_loans_when_all_categories_owned():
    """All loans should be upserted when every category_id belongs to the user."""
    from app.routers.sync import push_state
    from app.schemas.sync import AppStateIn

    user = _make_user("user-1")
    owned_cats = [_make_category("cat-A"), _make_category("cat-B")]

    mock_cat_repo = AsyncMock()
    mock_cat_repo.upsert = AsyncMock()
    mock_cat_repo.get_all = AsyncMock(return_value=owned_cats)

    mock_loan_repo = AsyncMock()
    mock_loan_repo.upsert = AsyncMock()
    mock_loan_repo.get_all = AsyncMock(return_value=[])

    mock_entry_repo = AsyncMock()
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    data = AppStateIn(
        selected_month="2024-01",
        categories=[_make_category_create("cat-A"), _make_category_create("cat-B")],
        loans=[
            _make_loan_create("loan-1", "cat-A"),
            _make_loan_create("loan-2", "cat-B"),
        ],
        month_entries=[],
    )

    with (
        patch("app.routers.sync.CategoryRepository", return_value=mock_cat_repo),
        patch("app.routers.sync.LoanRepository", return_value=mock_loan_repo),
        patch("app.routers.sync.MonthEntryRepository", return_value=mock_entry_repo),
        patch("app.routers.sync._get_entries_for_user", new=AsyncMock(return_value=[])),
    ):
        await push_state(data=data, db=mock_db, current_user=user)

    upserted_ids = [call.args[0].id for call in mock_loan_repo.upsert.call_args_list]
    assert "loan-1" in upserted_ids
    assert "loan-2" in upserted_ids


# ── Reconcile (deletion) tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_push_state_reconcile_issues_delete_statements():
    """push_state must issue exactly 2 reconcile DELETE statements (category + loan)
    so that records absent from the payload are removed server-side.

    This guards against the regression where push was upsert-only: items deleted
    while offline would silently reappear on the next pull.
    """
    from app.routers.sync import push_state
    from app.schemas.sync import AppStateIn

    user = _make_user("user-1")

    mock_cat_repo = AsyncMock()
    mock_cat_repo.upsert = AsyncMock()
    mock_cat_repo.get_all = AsyncMock(return_value=[])

    mock_loan_repo = AsyncMock()
    mock_loan_repo.upsert = AsyncMock()
    mock_loan_repo.get_all = AsyncMock(return_value=[])

    mock_entry_repo = AsyncMock()
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    # Empty payload — all server-side records should be reconcile-deleted.
    data = AppStateIn(
        selected_month="2024-01",
        categories=[],
        loans=[],
        month_entries=[],
    )

    with (
        patch("app.routers.sync.CategoryRepository", return_value=mock_cat_repo),
        patch("app.routers.sync.LoanRepository", return_value=mock_loan_repo),
        patch("app.routers.sync.MonthEntryRepository", return_value=mock_entry_repo),
        patch("app.routers.sync._get_entries_for_user", new=AsyncMock(return_value=[])),
    ):
        await push_state(data=data, db=mock_db, current_user=user)

    # Exactly 2 direct db.execute calls: one DELETE for categories, one for loans.
    assert mock_db.execute.call_count == 2, (
        f"Expected 2 reconcile-delete db.execute calls, got {mock_db.execute.call_count}"
    )


@pytest.mark.asyncio
async def test_push_state_reconcile_executes_even_with_payload():
    """Reconcile DELETEs run even when the payload is non-empty (NOT IN filter).

    When all records are present in the payload the DELETE matches 0 rows, but
    the statement must still be issued so newly-deleted items are cleaned up.
    """
    from app.routers.sync import push_state
    from app.schemas.sync import AppStateIn

    user = _make_user("user-1")
    owned_cats = [_make_category("cat-A"), _make_category("cat-B")]

    mock_cat_repo = AsyncMock()
    mock_cat_repo.upsert = AsyncMock()
    mock_cat_repo.get_all = AsyncMock(return_value=owned_cats)

    mock_loan_repo = AsyncMock()
    mock_loan_repo.upsert = AsyncMock()
    mock_loan_repo.get_all = AsyncMock(return_value=[])

    mock_entry_repo = AsyncMock()
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    data = AppStateIn(
        selected_month="2024-01",
        categories=[_make_category_create("cat-A"), _make_category_create("cat-B")],
        loans=[],
        month_entries=[],
    )

    with (
        patch("app.routers.sync.CategoryRepository", return_value=mock_cat_repo),
        patch("app.routers.sync.LoanRepository", return_value=mock_loan_repo),
        patch("app.routers.sync.MonthEntryRepository", return_value=mock_entry_repo),
        patch("app.routers.sync._get_entries_for_user", new=AsyncMock(return_value=[])),
    ):
        await push_state(data=data, db=mock_db, current_user=user)

    # Still 2 reconcile-delete calls even with a non-empty payload.
    assert mock_db.execute.call_count == 2
