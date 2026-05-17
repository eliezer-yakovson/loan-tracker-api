from pydantic import BaseModel

from app.schemas.category import CategoryCreate, CategoryRead
from app.schemas.loan import LoanCreate, LoanRead
from app.schemas.month_entry import MonthEntryRead, MonthEntryUpsert


class AppStateIn(BaseModel):
    """
    Full app state pushed from the React client.
    Mirrors the TypeScript AppState type.
    """
    selected_month: str                      # YYYY-MM
    categories: list[CategoryCreate]
    loans: list[LoanCreate]
    month_entries: list[MonthEntryUpsert]


class AppStateOut(BaseModel):
    """
    Full app state returned to the React client after a sync.
    """
    selected_month: str
    categories: list[CategoryRead]
    loans: list[LoanRead]
    month_entries: list[MonthEntryRead]
