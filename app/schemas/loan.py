from decimal import Decimal

from pydantic import BaseModel, Field


class LoanBase(BaseModel):
    category_id: str
    name: str
    lender_name: str = ""
    original_amount: Decimal = Field(gt=0)
    monthly_amount: Decimal = Field(gt=0)
    total_payments: int = Field(gt=0)
    taken_date: str              # YYYY-MM-DD
    monthly_due_day: int = Field(ge=1, le=31)
    notes: str = ""
    is_frozen: bool = False
    partial_percentage: Decimal = Field(default=Decimal("100.00"), ge=Decimal("1"), le=Decimal("100"))


class LoanCreate(LoanBase):
    """Client may provide a pre-generated id (mirroring the React app's makeId())."""
    id: str | None = None


class LoanRead(LoanBase):
    """Returned to the client."""
    id: str

    model_config = {"from_attributes": True}


class LoanUpdate(BaseModel):
    """All fields optional — PATCH semantics."""
    category_id: str | None = None
    name: str | None = None
    lender_name: str | None = None
    original_amount: Decimal | None = Field(default=None, gt=0)
    monthly_amount: Decimal | None = Field(default=None, gt=0)
    total_payments: int | None = Field(default=None, gt=0)
    taken_date: str | None = None
    monthly_due_day: int | None = Field(default=None, ge=1, le=31)
    notes: str | None = None
