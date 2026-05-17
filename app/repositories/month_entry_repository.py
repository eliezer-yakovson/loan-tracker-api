import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.month_entry import MonthEntry
from app.schemas.month_entry import MonthEntryCreate, MonthEntryUpdate, MonthEntryUpsert


class MonthEntryRepository:
    """All ORM queries for the month_entries table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Reads ────────────────────────────────────────────────────────────────

    async def get_all(self) -> list[MonthEntry]:
        result = await self.session.execute(
            select(MonthEntry).order_by(MonthEntry.month_key, MonthEntry.loan_id)
        )
        return list(result.scalars().all())

    async def get_all_for_month(self, month_key: str) -> list[MonthEntry]:
        result = await self.session.execute(
            select(MonthEntry).where(MonthEntry.month_key == month_key)
        )
        return list(result.scalars().all())

    async def get_all_for_loan(self, loan_id: str) -> list[MonthEntry]:
        result = await self.session.execute(
            select(MonthEntry)
            .where(MonthEntry.loan_id == loan_id)
            .order_by(MonthEntry.month_key)
        )
        return list(result.scalars().all())

    async def get_by_loan_and_month(
        self, loan_id: str, month_key: str
    ) -> MonthEntry | None:
        result = await self.session.execute(
            select(MonthEntry).where(
                MonthEntry.loan_id == loan_id,
                MonthEntry.month_key == month_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, entry_id: str) -> MonthEntry | None:
        return await self.session.get(MonthEntry, entry_id)

    async def get_all_month_keys(self) -> list[str]:
        """Sorted list of distinct month_key values (newest first)."""
        result = await self.session.execute(
            select(MonthEntry.month_key)
            .distinct()
            .order_by(MonthEntry.month_key.desc())
        )
        return list(result.scalars().all())

    # ── Writes ───────────────────────────────────────────────────────────────

    async def create(self, data: MonthEntryCreate) -> MonthEntry:
        entry = MonthEntry(
            id=data.id or str(uuid.uuid4()),
            **data.model_dump(exclude={"id"}),
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def upsert(self, data: MonthEntryUpsert) -> MonthEntry:
        """
        Insert or update using the (loan_id, month_key) unique constraint.
        The id column is preserved on conflict — only the mutable fields are updated.
        """
        entry_id = data.id or str(uuid.uuid4())
        stmt = (
            pg_insert(MonthEntry)
            .values(
                id=entry_id,
                loan_id=data.loan_id,
                month_key=data.month_key,
                amount=data.amount,
                installment_number=data.installment_number,
                confirmed=data.confirmed,
                manually_edited=data.manually_edited,
            )
            .on_conflict_do_update(
                constraint="uq_month_entries_loan_month",
                set_={
                    "amount": data.amount,
                    "installment_number": data.installment_number,
                    "confirmed": data.confirmed,
                    "manually_edited": data.manually_edited,
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        # Fetch after upsert to return a fully-loaded ORM object
        return await self.get_by_loan_and_month(data.loan_id, data.month_key)  # type: ignore[return-value]

    async def update(self, entry_id: str, data: MonthEntryUpdate) -> MonthEntry | None:
        entry = await self.get_by_id(entry_id)
        if not entry:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(entry, field, value)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def delete(self, entry_id: str) -> bool:
        result = await self.session.execute(
            delete(MonthEntry).where(MonthEntry.id == entry_id)
        )
        return result.rowcount > 0
