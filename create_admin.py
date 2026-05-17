"""
Run inside the Docker container to make a user admin:
  docker exec backend-api-1 python /code/create_admin.py e3251105@gmail.com
"""
import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def make_admin(email: str) -> None:
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://loan_user:loan_pass@db:5432/loan_tracker",
    )
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Import here so SQLAlchemy metadata is loaded
        from app.models.user import User  # noqa: PLC0415

        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"❌ משתמש עם מייל {email} לא נמצא")
            return
        user.is_admin = True
        await session.commit()
        print(f"✅ {user.name} ({user.email}) הוגדר כאדמין")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("שימוש: python create_admin.py <email>")
        sys.exit(1)
    asyncio.run(make_admin(sys.argv[1]))
