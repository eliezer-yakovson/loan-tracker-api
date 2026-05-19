import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryRepository:
    """All ORM queries for the categories table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Reads ────────────────────────────────────────────────────────────────

    async def get_all(self, user_id: str) -> list[Category]:
        result = await self.session.execute(
            select(Category).where(Category.user_id == user_id).order_by(Category.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, category_id: str) -> Category | None:
        return await self.session.get(Category, category_id)

    # ── Writes ───────────────────────────────────────────────────────────────

    async def create(self, data: CategoryCreate, user_id: str) -> Category:
        category = Category(
            id=data.id or str(uuid.uuid4()),
            user_id=user_id,
            name=data.name,
        )
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def upsert(self, data: CategoryCreate, user_id: str) -> Category:
        """Insert or update by primary key — used during full-state sync."""
        entry_id = data.id or str(uuid.uuid4())
        stmt = (
            pg_insert(Category)
            .values(id=entry_id, user_id=user_id, name=data.name)
            .on_conflict_do_update(
                index_elements=["id"],
                set_={"name": data.name},
                where=(Category.user_id == user_id),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.session.get(Category, entry_id)  # type: ignore[return-value]

    async def update(self, category_id: str, data: CategoryUpdate) -> Category | None:
        category = await self.get_by_id(category_id)
        if not category:
            return None
        if data.name is not None:
            category.name = data.name
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete(self, category_id: str) -> bool:
        result = await self.session.execute(
            delete(Category).where(Category.id == category_id)
        )
        return result.rowcount > 0
