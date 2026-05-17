from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: registers all ORM models with Base.metadata
from app.db.base import Base
from app.db.engine import engine
from app.routers import categories, loans, month_entries, sync
from app.routers import auth as auth_router
from app.routers import admin as admin_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    # On startup: create any tables that don't exist yet.
    # In production, use `alembic upgrade head` instead and remove this block.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Loan Tracker API",
    version="1.0.0",
    description="Backend for the Hebrew loan-tracking app. Stores data in PostgreSQL (Neon).",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
from app.config import settings as _settings
_cors_origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "http://localhost:3000",
    "https://localhost:3000",
]
if _settings.frontend_origin:
    _cors_origins.append(_settings.frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(categories.router)
app.include_router(loans.router)
app.include_router(month_entries.router)
app.include_router(sync.router)
app.include_router(auth_router.router)
app.include_router(admin_router.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
