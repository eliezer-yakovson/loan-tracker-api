import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("monthly_due_day BETWEEN 1 AND 31", name="ck_loans_due_day"),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lender_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_payments: Mapped[int] = mapped_column(Integer, nullable=False)
    taken_date: Mapped[str] = mapped_column(String(10), nullable=False)   # YYYY-MM-DD
    monthly_due_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    partial_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("100.00")
    )

    category: Mapped["Category"] = relationship(  # type: ignore[name-defined]
        "Category",
        back_populates="loans",
    )
    month_entries: Mapped[list["MonthEntry"]] = relationship(  # type: ignore[name-defined]
        "MonthEntry",
        back_populates="loan",
        cascade="all, delete-orphan",
    )
