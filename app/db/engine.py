from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# pool_pre_ping keeps Neon serverless connections healthy after idle periods
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    # Neon free tier: limit pool to avoid exhausting connections
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a DB session and ensures it is closed."""
    async with AsyncSessionLocal() as session:
        yield session
