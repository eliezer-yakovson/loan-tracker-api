import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MonthEntry(Base):
    __tablename__ = "month_entries"
    __table_args__ = (
        UniqueConstraint("loan_id", "month_key", name="uq_month_entries_loan_month"),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    loan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("loans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month_key: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
    )  # Format: YYYY-MM
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manually_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    loan: Mapped["Loan"] = relationship(  # type: ignore[name-defined]
        "Loan",
        back_populates="month_entries",
    )
