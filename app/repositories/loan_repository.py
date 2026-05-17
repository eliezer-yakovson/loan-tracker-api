import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import Loan
from app.schemas.loan import LoanCreate, LoanUpdate


class LoanRepository:
    """All ORM queries for the loans table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Reads ────────────────────────────────────────────────────────────────

    async def get_all(self, user_id: str) -> list[Loan]:
        result = await self.session.execute(
            select(Loan).where(Loan.user_id == user_id).order_by(Loan.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, loan_id: str) -> Loan | None:
        return await self.session.get(Loan, loan_id)

    async def get_by_category(self, category_id: str, user_id: str) -> list[Loan]:
        result = await self.session.execute(
            select(Loan)
            .where(Loan.category_id == category_id, Loan.user_id == user_id)
            .order_by(Loan.name)
        )
        return list(result.scalars().all())

    # ── Writes ───────────────────────────────────────────────────────────────

    async def create(self, data: LoanCreate, user_id: str) -> Loan:
        loan = Loan(
            id=data.id or str(uuid.uuid4()),
            user_id=user_id,
            **data.model_dump(exclude={"id"}),
        )
        self.session.add(loan)
        await self.session.flush()
        await self.session.refresh(loan)
        return loan

    async def upsert(self, data: LoanCreate, user_id: str) -> Loan:
        """Insert or update by primary key — used during full-state sync."""
        entry_id = data.id or str(uuid.uuid4())
        values = {"id": entry_id, "user_id": user_id, **data.model_dump(exclude={"id"})}
        set_values = {k: v for k, v in values.items() if k not in ("id", "user_id")}

        stmt = (
            pg_insert(Loan)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["id"],
                set_=set_values,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.session.get(Loan, entry_id)  # type: ignore[return-value]

    async def update(self, loan_id: str, data: LoanUpdate) -> Loan | None:
        loan = await self.get_by_id(loan_id)
        if not loan:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(loan, field, value)
        await self.session.flush()
        await self.session.refresh(loan)
        return loan

    async def delete(self, loan_id: str) -> bool:
        result = await self.session.execute(
            delete(Loan).where(Loan.id == loan_id)
        )
        return result.rowcount > 0
