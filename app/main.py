from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: registers all ORM models with Base.metadata
from app.config import settings as _settings
from app.db.base import Base
from app.db.engine import engine
from app.routers import categories, loans, month_entries, sync
from app.routers import auth as auth_router
from app.routers import admin as admin_router
from app.routers import error_logs as error_logs_router


def _validate_startup_security() -> None:
    """Fail fast if critical security settings are misconfigured."""
    email_configured = bool(_settings.brevo_api_key and _settings.email_from)

    if email_configured and _settings.debug:
        raise RuntimeError(
            "Security misconfiguration: DEBUG=true must not be used when email is "
            "configured (production environment). Set DEBUG=false."
        )


@asynccontextmanager
async def lifespan(application: FastAPI):
    _validate_startup_security()
    if _settings.debug:
        # Development only: auto-create missing tables.
        # In production always run `alembic upgrade head` before starting the server.
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
app.include_router(error_logs_router.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
