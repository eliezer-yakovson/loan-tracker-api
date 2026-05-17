from decimal import Decimal

from pydantic import BaseModel


class MonthEntryBase(BaseModel):
    loan_id: str
    month_key: str        # YYYY-MM
    amount: Decimal
    installment_number: int
    confirmed: bool = False
    manually_edited: bool = False


class MonthEntryCreate(MonthEntryBase):
    """Used when creating a brand-new entry."""
    id: str | None = None


class MonthEntryUpsert(MonthEntryBase):
    """
    Used during sync — insert or update based on the (loan_id, month_key) unique key.
    The client may or may not supply an id.
    """
    id: str | None = None


class MonthEntryRead(MonthEntryBase):
    """Returned to the client."""
    id: str

    model_config = {"from_attributes": True}


class MonthEntryUpdate(BaseModel):
    """All fields optional — PATCH semantics."""
    amount: Decimal | None = None
    installment_number: int | None = None
    confirmed: bool | None = None
    manually_edited: bool | None = None
