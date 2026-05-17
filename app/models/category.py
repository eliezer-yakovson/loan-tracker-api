import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Cascade delete: removing a category removes all its loans (and their entries)
    loans: Mapped[list["Loan"]] = relationship(  # type: ignore[name-defined]
        "Loan",
        back_populates="category",
        cascade="all, delete-orphan",
    )
